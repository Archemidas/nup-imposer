"""Multi-format image loader.

Supports JPG, PNG, TIFF, PSD, PDF inputs. Returns a normalized LoadedImage
with original DPI, dimensions, mode, and embedded ICC profile if present.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from PIL import Image


# Lazy imports so installing the package without a PDF library still works
def _import_pymupdf():
    try:
        import fitz  # PyMuPDF
        return fitz
    except ImportError as e:
        raise ImportError(
            "PyMuPDF is required for PDF input. Install with: pip install PyMuPDF"
        ) from e


def _import_psd_tools():
    try:
        from psd_tools import PSDImage
        return PSDImage
    except ImportError as e:
        raise ImportError(
            "psd-tools is required for PSD input. Install with: pip install psd-tools"
        ) from e


@dataclass
class LoadedImage:
    """A loaded image with metadata."""
    pil_image: Image.Image
    width_px: int
    height_px: int
    dpi_x: float
    dpi_y: float
    mode: str  # PIL mode: RGB, RGBA, CMYK, L, etc.
    icc_profile: Optional[bytes]
    source_path: Path
    source_format: str

    @property
    def width_in(self) -> float:
        return self.width_px / self.dpi_x if self.dpi_x else 0.0

    @property
    def height_in(self) -> float:
        return self.height_px / self.dpi_y if self.dpi_y else 0.0

    @property
    def aspect(self) -> float:
        return self.width_px / self.height_px if self.height_px else 1.0


def load_image(path: str | Path, pdf_render_dpi: int = 300) -> LoadedImage:
    """Load an image from any supported format.

    Args:
        path: Path to the file.
        pdf_render_dpi: For PDF inputs, render the first page at this DPI.

    Returns:
        LoadedImage with original metadata preserved where possible.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Input not found: {path}")

    ext = path.suffix.lower()

    if ext in (".jpg", ".jpeg", ".jpe", ".jfif"):
        return _load_via_pil(path, "JPEG")
    if ext == ".png":
        return _load_via_pil(path, "PNG")
    if ext in (".tif", ".tiff"):
        return _load_via_pil(path, "TIFF")
    if ext == ".psd":
        return _load_psd(path)
    if ext == ".pdf":
        return _load_pdf(path, pdf_render_dpi)
    raise ValueError(f"Unsupported format: {ext}")


def _load_via_pil(path: Path, fmt: str) -> LoadedImage:
    img = Image.open(path)
    img.load()  # force read - otherwise lazy and metadata may not be available

    dpi = img.info.get("dpi", (72.0, 72.0))
    if isinstance(dpi, (int, float)):
        dpi_x = dpi_y = float(dpi)
    else:
        dpi_x, dpi_y = float(dpi[0]), float(dpi[1])

    icc = img.info.get("icc_profile")

    return LoadedImage(
        pil_image=img,
        width_px=img.width,
        height_px=img.height,
        dpi_x=dpi_x,
        dpi_y=dpi_y,
        mode=img.mode,
        icc_profile=icc,
        source_path=path,
        source_format=fmt,
    )


def _load_psd(path: Path) -> LoadedImage:
    PSDImage = _import_psd_tools()
    psd = PSDImage.open(path)
    img = psd.composite()
    if img is None:
        raise ValueError(f"PSD has no composite image: {path}")
    # psd_tools doesn't expose DPI directly; fall back to 72 unless header says otherwise
    dpi_x = dpi_y = float(getattr(psd, "resolution", 72.0)) or 72.0
    icc = getattr(psd, "icc_profile", None)
    return LoadedImage(
        pil_image=img,
        width_px=img.width,
        height_px=img.height,
        dpi_x=dpi_x,
        dpi_y=dpi_y,
        mode=img.mode,
        icc_profile=icc,
        source_path=path,
        source_format="PSD",
    )


def _load_pdf(path: Path, render_dpi: int) -> LoadedImage:
    fitz = _import_pymupdf()
    doc = fitz.open(path)
    try:
        if doc.page_count == 0:
            raise ValueError(f"PDF has no pages: {path}")
        page = doc.load_page(0)
        # Render at requested DPI
        zoom = render_dpi / 72.0
        matrix = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        mode = "RGB" if pix.n < 4 else "RGBA"
        img = Image.frombytes(mode, (pix.width, pix.height), pix.samples)
        return LoadedImage(
            pil_image=img,
            width_px=img.width,
            height_px=img.height,
            dpi_x=float(render_dpi),
            dpi_y=float(render_dpi),
            mode=img.mode,
            icc_profile=None,
            source_path=path,
            source_format="PDF",
        )
    finally:
        doc.close()
