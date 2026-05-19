"""
imposer.py — Core n-up imposition logic for the web app.

Two layout modes:
  AUTO  — user sets image print size; rows/cols are calculated from canvas.
  GRID  — user sets rows/cols; cell size is calculated from canvas.

Preview is rendered as JPEG at a low DPI (96 by default).
Export is a PDF with images embedded at full resolution.
"""
from __future__ import annotations

import io
import math
from dataclasses import dataclass, field
from typing import Optional

from PIL import Image
import fitz  # PyMuPDF


# ---------------------------------------------------------------------------
# Paper sizes — (width_mm, height_mm) in PORTRAIT orientation
# ---------------------------------------------------------------------------
PAPER_SIZES: dict[str, tuple[float, float]] = {
    "letter":   (215.9,  279.4),
    "legal":    (215.9,  355.6),
    "tabloid":  (279.4,  431.8),
    "a3":       (297.0,  420.0),
    "a4":       (210.0,  297.0),
    "a5":       (148.0,  210.0),
    "4x6":      (101.6,  152.4),
    "5x7":      (127.0,  177.8),
    "8x10":     (203.2,  254.0),
    "8.5x11":   (215.9,  279.4),   # alias for letter
}

MM_PER_INCH = 25.4
PT_PER_INCH = 72.0


# ---------------------------------------------------------------------------
# Unit helpers
# ---------------------------------------------------------------------------
def mm_to_pt(mm: float) -> float:
    return mm * PT_PER_INCH / MM_PER_INCH


def mm_to_px(mm: float, dpi: float) -> int:
    return max(1, round(mm * dpi / MM_PER_INCH))


def inches_to_mm(v: float) -> float:
    return v * MM_PER_INCH


def cm_to_mm(v: float) -> float:
    return v * 10.0


# ---------------------------------------------------------------------------
# Settings dataclasses
# ---------------------------------------------------------------------------
@dataclass
class CanvasSettings:
    """Physical canvas (paper) size."""
    width_mm: float
    height_mm: float
    orientation: str = "portrait"   # "portrait" | "landscape"

    def effective_wh(self) -> tuple[float, float]:
        """Return (w, h) with orientation applied."""
        w, h = self.width_mm, self.height_mm
        if self.orientation == "landscape":
            return (max(w, h), min(w, h))
        return (min(w, h), max(w, h))


@dataclass
class ImageSettings:
    """Intended print size of each image cell."""
    width_mm: float
    height_mm: float
    orientation: str = "auto"   # "portrait" | "landscape" | "auto"
    fit: str = "contain"        # "contain" (letterbox) | "fill" (stretch)

    def effective_wh(self) -> tuple[float, float]:
        w, h = self.width_mm, self.height_mm
        if self.orientation == "portrait":
            return (min(w, h), max(w, h))
        if self.orientation == "landscape":
            return (max(w, h), min(w, h))
        return (w, h)


@dataclass
class LayoutSettings:
    """N-up grid and spacing."""
    mode: str = "auto"          # "auto" (derive rows/cols) | "grid" (fixed rows/cols)
    rows: int = 2
    cols: int = 2
    margin_mm: float = 12.7     # uniform border margin (~0.5 inch)
    gutter_h_mm: float = 6.35   # horizontal gap between columns
    gutter_v_mm: float = 6.35   # vertical gap between rows


@dataclass
class ExportSettings:
    dpi: int = 300


@dataclass
class NupJob:
    canvas: CanvasSettings
    image: ImageSettings
    layout: LayoutSettings
    export: ExportSettings = field(default_factory=ExportSettings)


# ---------------------------------------------------------------------------
# Layout calculations
# ---------------------------------------------------------------------------
def resolve_layout(job: NupJob) -> tuple[int, int, float, float]:
    """
    Return (rows, cols, cell_w_mm, cell_h_mm) for a job.

    AUTO mode: image size is fixed; derive rows/cols that fill the canvas.
    GRID mode: rows/cols are fixed; derive cell size that fills the canvas.
    """
    cw, ch = job.canvas.effective_wh()
    L = job.layout
    usable_w = cw - 2 * L.margin_mm
    usable_h = ch - 2 * L.margin_mm

    if L.mode == "auto":
        iw, ih = job.image.effective_wh()
        cols = max(1, math.floor((usable_w + L.gutter_h_mm) / (iw + L.gutter_h_mm)))
        rows = max(1, math.floor((usable_h + L.gutter_v_mm) / (ih + L.gutter_v_mm)))
        return rows, cols, iw, ih
    else:
        rows, cols = max(1, L.rows), max(1, L.cols)
        cell_w = (usable_w - (cols - 1) * L.gutter_h_mm) / cols
        cell_h = (usable_h - (rows - 1) * L.gutter_v_mm) / rows
        return rows, cols, max(1.0, cell_w), max(1.0, cell_h)


def cell_rects_mm(
    canvas_w: float, canvas_h: float,
    cell_w: float, cell_h: float,
    rows: int, cols: int,
    margin: float, gutter_h: float, gutter_v: float,
) -> list[tuple[float, float, float, float]]:
    """Row-major list of (x, y, w, h) in mm for each cell."""
    out = []
    for r in range(rows):
        for c in range(cols):
            x = margin + c * (cell_w + gutter_h)
            y = margin + r * (cell_h + gutter_v)
            out.append((x, y, cell_w, cell_h))
    return out


# ---------------------------------------------------------------------------
# Image helpers
# ---------------------------------------------------------------------------
def _open_rgb(data: bytes) -> Image.Image:
    img = Image.open(io.BytesIO(data))
    if img.mode == "RGBA":
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[3])
        img = bg
    elif img.mode != "RGB":
        img = img.convert("RGB")
    return img


def _fit_to_cell(src: Image.Image, w_px: int, h_px: int, fit: str) -> Image.Image:
    if fit == "fill":
        return src.resize((w_px, h_px), Image.LANCZOS)
    # contain: shrink-to-fit, white letterbox
    ratio = min(w_px / src.width, h_px / src.height)
    new_w = round(src.width * ratio)
    new_h = round(src.height * ratio)
    scaled = src.resize((new_w, new_h), Image.LANCZOS)
    out = Image.new("RGB", (w_px, h_px), (255, 255, 255))
    out.paste(scaled, ((w_px - new_w) // 2, (h_px - new_h) // 2))
    return out


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def render_preview(image_bytes: bytes, job: NupJob, preview_dpi: int = 96) -> bytes:
    """Return JPEG bytes of the composed layout at preview_dpi."""
    cw_mm, ch_mm = job.canvas.effective_wh()
    rows, cols, cell_w_mm, cell_h_mm = resolve_layout(job)
    L = job.layout

    rects = cell_rects_mm(
        cw_mm, ch_mm, cell_w_mm, cell_h_mm,
        rows, cols, L.margin_mm, L.gutter_h_mm, L.gutter_v_mm,
    )

    canvas_w_px = mm_to_px(cw_mm, preview_dpi)
    canvas_h_px = mm_to_px(ch_mm, preview_dpi)
    cell_w_px   = mm_to_px(cell_w_mm, preview_dpi)
    cell_h_px   = mm_to_px(cell_h_mm, preview_dpi)

    src = _open_rgb(image_bytes)
    cell_img = _fit_to_cell(src, cell_w_px, cell_h_px, job.image.fit)

    canvas = Image.new("RGB", (canvas_w_px, canvas_h_px), (255, 255, 255))
    for x_mm, y_mm, _w, _h in rects:
        canvas.paste(cell_img, (mm_to_px(x_mm, preview_dpi), mm_to_px(y_mm, preview_dpi)))

    buf = io.BytesIO()
    canvas.save(buf, format="JPEG", quality=82, optimize=True)
    return buf.getvalue()


def generate_pdf(image_bytes: bytes, job: NupJob) -> bytes:
    """Return PDF bytes with full-resolution n-up layout."""
    cw_mm, ch_mm = job.canvas.effective_wh()
    rows, cols, cell_w_mm, cell_h_mm = resolve_layout(job)
    L, E = job.layout, job.export

    rects = cell_rects_mm(
        cw_mm, ch_mm, cell_w_mm, cell_h_mm,
        rows, cols, L.margin_mm, L.gutter_h_mm, L.gutter_v_mm,
    )

    cell_w_px = mm_to_px(cell_w_mm, E.dpi)
    cell_h_px = mm_to_px(cell_h_mm, E.dpi)

    src = _open_rgb(image_bytes)
    cell_img = _fit_to_cell(src, cell_w_px, cell_h_px, job.image.fit)

    # Embed as PNG for lossless quality inside the PDF
    img_buf = io.BytesIO()
    cell_img.save(img_buf, format="PNG")
    img_data = img_buf.getvalue()

    doc = fitz.open()
    page = doc.new_page(width=mm_to_pt(cw_mm), height=mm_to_pt(ch_mm))

    for x_mm, y_mm, w_mm, h_mm in rects:
        rect = fitz.Rect(
            mm_to_pt(x_mm), mm_to_pt(y_mm),
            mm_to_pt(x_mm + w_mm), mm_to_pt(y_mm + h_mm),
        )
        page.insert_image(rect, stream=img_data)

    pdf_buf = io.BytesIO()
    doc.save(pdf_buf)
    doc.close()
    pdf_buf.seek(0)
    return pdf_buf.getvalue()


def layout_info(job: NupJob) -> dict:
    """Return a summary dict for display in the UI."""
    rows, cols, cell_w_mm, cell_h_mm = resolve_layout(job)
    cw_mm, ch_mm = job.canvas.effective_wh()
    return {
        "rows": rows,
        "cols": cols,
        "count": rows * cols,
        "cell_w_mm": round(cell_w_mm, 2),
        "cell_h_mm": round(cell_h_mm, 2),
        "cell_w_in": round(cell_w_mm / MM_PER_INCH, 3),
        "cell_h_in": round(cell_h_mm / MM_PER_INCH, 3),
        "canvas_w_mm": round(cw_mm, 2),
        "canvas_h_mm": round(ch_mm, 2),
    }
