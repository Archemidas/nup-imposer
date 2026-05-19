"""TIFF and PDF exporters for imposed layouts.

Output is designed to open cleanly in Adobe Photoshop and Adobe Acrobat:
- TIFF: LZW compression, embedded ICC, accurate DPI tags
- PDF: image placed at exact physical inch dimensions, embedded JPEG/Flate

Phase 2: optional active ICC transform before save. When `dest_profile` is
supplied, the composited canvas is converted from the source profile (the
image's embedded ICC, or assumed sRGB if none) to the destination profile
using the specified rendering intent. The destination profile is then
embedded in the output.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional, Union

from PIL import Image

from .color import (
    ColorSettings,
    ProfileSource,
    RenderingIntent,
    apply_transform,
    ensure_source_profile,
    profile_bytes_from_source,
)
from .image_loader import LoadedImage
from .imposition import ImpositionLayout


def _composite(
    image: LoadedImage,
    layout: ImpositionLayout,
    output_dpi: int,
) -> Image.Image:
    """Composite all imposed cells onto a canvas at the target DPI.

    Returns a PIL Image in the same color mode as the source where possible.
    """
    canvas_w_px = int(round(layout.paper.width_in * output_dpi))
    canvas_h_px = int(round(layout.paper.height_in * output_dpi))

    mode = image.mode if image.mode in ("RGB", "RGBA", "CMYK", "L") else "RGB"

    if mode == "CMYK":
        bg: Union[int, tuple] = (0, 0, 0, 0)
    elif mode == "L":
        bg = 255
    elif mode == "RGBA":
        bg = (255, 255, 255, 255)
    else:
        bg = (255, 255, 255)

    canvas = Image.new(mode, (canvas_w_px, canvas_h_px), bg)

    src = image.pil_image
    if src.mode != mode:
        src = src.convert(mode)

    for cell in layout.cells:
        cell_w_px = int(round(cell.width_in * output_dpi))
        cell_h_px = int(round(cell.height_in * output_dpi))
        if cell_w_px <= 0 or cell_h_px <= 0:
            continue
        if cell.rotated:
            pre_w, pre_h = cell_h_px, cell_w_px
        else:
            pre_w, pre_h = cell_w_px, cell_h_px

        resized = src.resize((pre_w, pre_h), Image.LANCZOS)
        if cell.rotated:
            resized = resized.rotate(90, expand=True)
        x_px = int(round(cell.x_in * output_dpi))
        y_px = int(round(cell.y_in * output_dpi))
        canvas.paste(resized, (x_px, y_px))

    return canvas


def _maybe_apply_color_transform(
    canvas: Image.Image,
    image: LoadedImage,
    dest_profile: Optional[ProfileSource],
    intent: RenderingIntent,
    black_point_compensation: bool,
) -> tuple[Image.Image, Optional[bytes]]:
    """If dest_profile is set, transform canvas. Return (canvas, icc_bytes_to_embed).

    The icc_bytes_to_embed is either the destination profile bytes (after
    transform) or the original embedded ICC (if no transform). May be None
    when nothing should be embedded.
    """
    if dest_profile is None:
        return canvas, image.icc_profile

    source = ensure_source_profile(image.icc_profile, canvas.mode)
    transformed = apply_transform(
        canvas,
        source_profile=source,
        dest_profile=dest_profile,
        intent=intent,
        black_point_compensation=black_point_compensation,
    )
    dest_bytes = profile_bytes_from_source(dest_profile)
    return transformed, dest_bytes


def _maybe_mirror(canvas: Image.Image, mirror: bool) -> Image.Image:
    """Horizontally flip the canvas if mirror is True (for sublimation)."""
    if mirror:
        return canvas.transpose(Image.FLIP_LEFT_RIGHT)
    return canvas


def export_tiff(
    image: LoadedImage,
    layout: ImpositionLayout,
    output_path: str | Path,
    output_dpi: int = 300,
    compression: str = "tiff_lzw",
    preserve_icc: bool = True,
    *,
    dest_profile: Optional[ProfileSource] = None,
    intent: RenderingIntent = RenderingIntent.PERCEPTUAL,
    black_point_compensation: bool = True,
    color_settings: Optional[ColorSettings] = None,
) -> Path:
    """Composite and save as TIFF preserving ICC and DPI metadata.

    Args:
        image: Source image with metadata.
        layout: Imposition layout to apply.
        output_path: Destination file path.
        output_dpi: Target DPI.
        compression: TIFF compression ('tiff_lzw', 'tiff_deflate', 'none').
        preserve_icc: If True, embed the active ICC profile in the output.
        dest_profile: If set, transform colors to this profile before saving.
        intent: Rendering intent for the transform.
        black_point_compensation: Whether to enable BPC during transform.
        color_settings: Convenience bundle that overrides the above if set.
    """
    mirror = False
    if color_settings is not None:
        dest_profile = color_settings.dest_source()
        intent = color_settings.intent
        black_point_compensation = color_settings.black_point_compensation
        mirror = color_settings.mirror_output

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    canvas = _composite(image, layout, output_dpi)
    canvas, icc_to_embed = _maybe_apply_color_transform(
        canvas, image, dest_profile, intent, black_point_compensation,
    )
    canvas = _maybe_mirror(canvas, mirror)

    save_kwargs: dict = {
        "format": "TIFF",
        "dpi": (output_dpi, output_dpi),
        "compression": compression,
    }
    if preserve_icc and icc_to_embed:
        save_kwargs["icc_profile"] = icc_to_embed

    canvas.save(output_path, **save_kwargs)
    return output_path


def export_pdf(
    image: LoadedImage,
    layout: ImpositionLayout,
    output_path: str | Path,
    output_dpi: int = 300,
    preserve_icc: bool = True,
    *,
    dest_profile: Optional[ProfileSource] = None,
    intent: RenderingIntent = RenderingIntent.PERCEPTUAL,
    black_point_compensation: bool = True,
    color_settings: Optional[ColorSettings] = None,
) -> Path:
    """Composite and save as PDF with correct page size and embedded image.

    The output PDF has a single page sized to the paper dimensions in inches,
    making it open at the intended physical size in Acrobat.
    """
    mirror = False
    if color_settings is not None:
        dest_profile = color_settings.dest_source()
        intent = color_settings.intent
        black_point_compensation = color_settings.black_point_compensation
        mirror = color_settings.mirror_output

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    canvas = _composite(image, layout, output_dpi)
    canvas, _icc_to_embed = _maybe_apply_color_transform(
        canvas, image, dest_profile, intent, black_point_compensation,
    )
    canvas = _maybe_mirror(canvas, mirror)

    save_kwargs: dict = {
        "format": "PDF",
        "resolution": float(output_dpi),
    }

    canvas.save(output_path, **save_kwargs)
    return output_path
