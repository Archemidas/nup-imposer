"""TIFF and PDF exporters for imposed layouts.

Output is designed to open cleanly in Adobe Photoshop and Adobe Acrobat:
- TIFF: LZW compression, embedded ICC, accurate DPI tags
- PDF: image placed at exact physical inch dimensions, embedded JPEG/Flate

Phase 2: optional active ICC transform before save.
Phase 4: multi-channel TIFF export (DeviceN) for RIP-ready output.
         When `tifffile` is installed, produces a single separated TIFF
         with ink channel names embedded in the InkNames TIFF tag.
         When `tifffile` is absent, falls back to N individual 8-bit
         grayscale TIFFs named <output>_<abbreviation>.tif.
"""
from __future__ import annotations

import struct
import zlib
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

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


# ---------------------------------------------------------------------------
# DeviceN TIFF writer (pure Python, no external deps)
# ---------------------------------------------------------------------------

def _build_devicen_tiff(
    channel_images: List[Image.Image],
    channel_names: List[str],
    output_dpi: int,
    icc_bytes: Optional[bytes] = None,
) -> bytes:
    """Build a planar DeviceN (Separated) TIFF as raw bytes.

    Uses PlanarConfiguration=2 (planar) so all pixels of each channel are
    stored contiguously.  Compression is DEFLATE (zlib) per channel plane.

    Handles an arbitrary number of 8-bit 'L' mode channel images.
    Embeds ICC bytes via tag 34675 (ICCProfile) when provided.
    """
    n = len(channel_images)
    assert n >= 1, "At least one channel required"
    w, h = channel_images[0].size

    LE = "<"  # little-endian TIFF

    def u16(v: int) -> bytes:
        return struct.pack(LE + "H", int(v))

    def u32(v: int) -> bytes:
        return struct.pack(LE + "I", int(v))

    def rational(num: int, den: int) -> bytes:
        return struct.pack(LE + "II", int(num), int(den))

    # ------------------------------------------------------------------
    # Build compressed channel planes
    # ------------------------------------------------------------------
    planes: List[bytes] = []
    for img in channel_images:
        raw = img.tobytes() if img.mode == "L" else img.convert("L").tobytes()
        planes.append(zlib.compress(raw, level=6))

    # ------------------------------------------------------------------
    # Compute TIFF layout
    # ------------------------------------------------------------------
    # Header: 8 bytes
    # IFD count: 2 bytes
    # IFD entries: 12 bytes each
    # Next-IFD pointer: 4 bytes
    # Extra data (arrays, strings, rationals) immediately after IFD
    # Then channel planes

    # Required tags sorted by tag number (TIFF spec requirement)
    # We'll compute offsets in two passes.

    # Assemble extra-data block (variable-length values):
    extra_data: List[bytes] = []  # aligned accumulator
    extra_offset_base = 0  # filled in once we know IFD size

    # --- BitsPerSample: n × SHORT(8) ---
    bits_data = b"".join(u16(8) for _ in range(n))
    bps_offset_slot = len(extra_data)  # index, not yet absolute offset
    extra_data.append(bits_data)

    # --- StripOffsets: n × LONG (one strip per plane) ---
    so_offset_slot = len(extra_data)
    # Placeholder – real offsets computed after layout
    extra_data.append(b"\x00" * (4 * n))

    # --- StripByteCounts: n × LONG ---
    sbc_data = b"".join(u32(len(p)) for p in planes)
    sbc_offset_slot = len(extra_data)
    extra_data.append(sbc_data)

    # --- XResolution + YResolution: 2 × RATIONAL(8 bytes each) ---
    xres_data = rational(output_dpi, 1)
    xres_offset_slot = len(extra_data)
    extra_data.append(xres_data)

    yres_data = rational(output_dpi, 1)
    yres_offset_slot = len(extra_data)
    extra_data.append(yres_data)

    # --- InkNames: null-separated channel names, null-terminated ---
    ink_names_str = "\x00".join(channel_names) + "\x00"
    ink_names_bytes = ink_names_str.encode("ascii", errors="replace")
    inames_offset_slot = len(extra_data)
    extra_data.append(ink_names_bytes)

    # --- ICC profile (optional) ---
    icc_offset_slot = -1
    if icc_bytes:
        icc_offset_slot = len(extra_data)
        extra_data.append(icc_bytes)

    # Build the ordered tag list (tag, type, count, inline_value_or_None)
    # type codes: 1=BYTE, 2=ASCII, 3=SHORT, 4=LONG, 5=RATIONAL
    BYTE, ASCII, SHORT, LONG, RATIONAL = 1, 2, 3, 4, 5

    tag_defs: List[Tuple] = [
        (256, LONG,     1, w),                           # ImageWidth
        (257, LONG,     1, h),                           # ImageLength
        (258, SHORT,    n, bps_offset_slot),             # BitsPerSample (offset)
        (259, SHORT,    1, 8),                           # Compression: DEFLATE
        (262, SHORT,    1, 5),                           # PhotometricInterpretation: Separated
        (273, LONG,     n, so_offset_slot),              # StripOffsets (offset)
        (277, SHORT,    1, n),                           # SamplesPerPixel
        (278, LONG,     1, h),                           # RowsPerStrip = entire image
        (279, LONG,     n, sbc_offset_slot),             # StripByteCounts (offset)
        (282, RATIONAL, 1, xres_offset_slot),            # XResolution (offset)
        (283, RATIONAL, 1, yres_offset_slot),            # YResolution (offset)
        (284, SHORT,    1, 2),                           # PlanarConfiguration: planar
        (296, SHORT,    1, 2),                           # ResolutionUnit: inch
        (332, SHORT,    1, 2),                           # InkSet: not CMYK
        (333, BYTE,     len(ink_names_bytes), inames_offset_slot),  # InkNames (offset)
        (334, SHORT,    1, n),                           # NumberOfInks
    ]

    if icc_bytes and icc_offset_slot >= 0:
        tag_defs.append((34675, BYTE, len(icc_bytes), icc_offset_slot))  # ICCProfile

    tag_defs.sort(key=lambda t: t[0])

    # ------------------------------------------------------------------
    # Compute absolute offsets
    # ------------------------------------------------------------------
    n_tags = len(tag_defs)
    ifd_offset = 8                             # IFD starts after 8-byte TIFF header
    ifd_size = 2 + 12 * n_tags + 4            # count + entries + next-ifd ptr
    extra_start = ifd_offset + ifd_size        # extra data starts here

    # Compute each extra_data block's absolute offset
    extra_offsets: List[int] = []
    pos = extra_start
    for blob in extra_data:
        # Align to 2-byte boundary
        if pos % 2:
            pos += 1
        extra_offsets.append(pos)
        pos += len(blob)

    # Pixel data starts after extra data (aligned)
    if pos % 2:
        pos += 1
    pixel_data_start = pos

    # Now compute strip offsets (one per plane)
    strip_offsets: List[int] = []
    ppos = pixel_data_start
    for p in planes:
        strip_offsets.append(ppos)
        ppos += len(p)

    # Patch StripOffsets data in extra_data
    so_data = b"".join(u32(off) for off in strip_offsets)
    extra_data[so_offset_slot] = so_data

    # ------------------------------------------------------------------
    # Assemble the TIFF bytes
    # ------------------------------------------------------------------
    buf = bytearray()

    # Header
    buf += b"II"          # little-endian
    buf += u16(42)        # TIFF magic
    buf += u32(ifd_offset)

    # IFD
    buf += u16(n_tags)
    for tag, dtype, count, value_or_slot in tag_defs:
        buf += u16(tag)
        buf += u16(dtype)
        buf += u32(count)

        # Determine if value fits inline (≤ 4 bytes) or needs an offset
        # Inline rule: total bytes for (type × count) ≤ 4
        type_sizes = {BYTE: 1, ASCII: 1, SHORT: 2, LONG: 4, RATIONAL: 8}
        total_bytes = type_sizes[dtype] * count

        if total_bytes <= 4 and isinstance(value_or_slot, int) and value_or_slot < 65536:
            # Inline value – left-justified with zero padding to 4 bytes
            if dtype == SHORT:
                raw_val = u16(value_or_slot) + b"\x00\x00"
            elif dtype == LONG:
                raw_val = u32(value_or_slot)
            else:
                raw_val = struct.pack(LE + "B", value_or_slot) + b"\x00\x00\x00"
            buf += raw_val
        else:
            # Offset into extra_data
            slot = value_or_slot
            buf += u32(extra_offsets[slot])

    buf += u32(0)  # next IFD pointer = 0 (no more IFDs)

    # Extra data blocks (with alignment padding)
    cur = extra_start
    for blob, off in zip(extra_data, extra_offsets):
        while cur < off:
            buf += b"\x00"
            cur += 1
        buf += blob
        cur += len(blob)

    # Pixel data alignment
    while cur % 2:
        buf += b"\x00"
        cur += 1

    # Pixel planes
    for p in planes:
        buf += p
        cur += len(p)

    return bytes(buf)


# ---------------------------------------------------------------------------
# Multi-channel export
# ---------------------------------------------------------------------------

def export_multichannel_tiff(
    image: LoadedImage,
    layout: ImpositionLayout,
    output_path: "str | Path",
    ink_set: "InkSet",                      # type: ignore[name-defined]
    output_dpi: int = 300,
    *,
    color_settings: Optional[ColorSettings] = None,
) -> Tuple[Path, bool]:
    """Composite and save as a multi-channel separated TIFF for RIP ingestion.

    The composited canvas is converted to CMYK (after any ICC transform),
    then split into the ink set's channels using the light-ink threshold model.

    Output strategy:
      1. If ``tifffile`` is installed: write a single DeviceN TIFF with
         InkNames and a proper Separated photometric tag.
      2. Otherwise: attempt our built-in pure-Python TIFF writer which uses
         DEFLATE compression and planar layout.
      3. If both fail: fall back to N individual grayscale TIFF files named
         ``<stem>_<ABBREVIATION>.tif``.

    Args:
        image:        Loaded source image.
        layout:       Imposition layout.
        output_path:  Destination file path (used for single-file DeviceN).
        ink_set:      Target ink set defining channels and TAC limit.
        output_dpi:   Output resolution in dots per inch.
        color_settings: Optional ICC transform / mirror settings.

    Returns:
        ``(output_path, is_single_file)`` where ``is_single_file`` is True
        when a single DeviceN TIFF was written, False when individual channel
        files were produced.
    """
    from .tac import channel_split  # avoid circular import at module level

    # -- Type import --
    InkSet = ink_set.__class__  # noqa: F841  (used for isinstance elsewhere)

    mirror = color_settings.mirror_output if color_settings else False

    canvas = _composite(image, layout, output_dpi)

    if color_settings is not None:
        canvas, _ = _maybe_apply_color_transform(
            canvas, image,
            color_settings.dest_source(),
            color_settings.intent,
            color_settings.black_point_compensation,
        )
    canvas = _maybe_mirror(canvas, mirror)

    # Convert to CMYK for splitting
    if canvas.mode != "CMYK":
        canvas = canvas.convert("CMYK")

    channel_images = channel_split(canvas, ink_set)
    channel_names = ink_set.channel_names

    # Embed ICC if we have one
    icc_bytes: Optional[bytes] = None
    if color_settings is not None and color_settings.has_destination():
        dest = color_settings.dest_source()
        if dest is not None:
            try:
                icc_bytes = profile_bytes_from_source(dest)
            except Exception:
                icc_bytes = None

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # --- Strategy 1: tifffile ---
    try:
        import tifffile  # type: ignore
        import numpy as np  # type: ignore

        W, H = canvas.size
        N = len(channel_images)
        data = np.zeros((H, W, N), dtype=np.uint8)
        for i, ch_img in enumerate(channel_images):
            raw = ch_img.tobytes()
            data[:, :, i] = np.frombuffer(raw, dtype=np.uint8).reshape(H, W)

        ink_names_str = "\x00".join(channel_names) + "\x00"
        ink_names_data = ink_names_str.encode("ascii", errors="replace")

        # tifffile tag format: (code, dtype_char, count, value, writeonce)
        extratags = [
            (332, "H", 1, 2, False),                              # InkSet = not CMYK
            (333, "B", len(ink_names_data), ink_names_data, True),# InkNames
            (334, "H", 1, N, False),                               # NumberOfInks
        ]
        if icc_bytes:
            extratags.append((34675, "B", len(icc_bytes), icc_bytes, True))

        tifffile.imwrite(
            str(output_path),
            data,
            photometric="separated",
            compression="lzw",
            resolutionunit=tifffile.RESUNIT.INCH,
            resolution=(output_dpi, output_dpi),
            extratags=extratags,
        )
        return output_path, True

    except (ImportError, Exception):
        pass

    # --- Strategy 2: built-in pure-Python DeviceN writer ---
    try:
        tiff_bytes = _build_devicen_tiff(
            channel_images, channel_names, output_dpi, icc_bytes
        )
        output_path.write_bytes(tiff_bytes)
        return output_path, True
    except Exception:
        pass

    # --- Strategy 3: per-channel grayscale TIFFs ---
    stem = output_path.stem
    parent = output_path.parent
    for ch_img, ch in zip(channel_images, ink_set.channels):
        ch_path = parent / f"{stem}_{ch.abbreviation}.tif"
        ch_img.save(str(ch_path), format="TIFF", dpi=(output_dpi, output_dpi))

    return output_path, False


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
