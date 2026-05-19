"""Live layout preview widget."""
from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QBrush, QColor, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import QWidget

from ..core.image_loader import LoadedImage
from ..core.imposition import ImpositionLayout


class PreviewWidget(QWidget):
    """Renders the imposition layout to scale, with image thumbnails in cells."""

    def __init__(self) -> None:
        super().__init__()
        self.setMinimumSize(400, 500)
        self._layout: Optional[ImpositionLayout] = None
        self._thumb: Optional[QPixmap] = None
        self.setStyleSheet("background: #f0f0f0;")

    def set_layout(self, layout: ImpositionLayout, image: LoadedImage) -> None:
        self._layout = layout
        # Build a small thumbnail of the source image
        try:
            from PIL.ImageQt import ImageQt
            pil_thumb = image.pil_image.copy()
            pil_thumb.thumbnail((400, 400))
            if pil_thumb.mode == "CMYK":
                pil_thumb = pil_thumb.convert("RGB")
            qim = ImageQt(pil_thumb)
            self._thumb = QPixmap.fromImage(qim)
        except Exception:
            self._thumb = None
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt convention
        painter = QPainter(self)
        painter.setRenderHints(
            QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform
        )

        # Background
        painter.fillRect(self.rect(), QColor("#f0f0f0"))

        if self._layout is None:
            painter.setPen(QColor("#999"))
            painter.drawText(
                self.rect(),
                Qt.AlignmentFlag.AlignCenter,
                "Layout preview will appear here",
            )
            return

        layout = self._layout
        paper_w_in = layout.paper.width_in
        paper_h_in = layout.paper.height_in

        # Fit paper into widget with padding
        pad = 30.0
        avail_w = self.width() - 2 * pad
        avail_h = self.height() - 2 * pad
        scale = min(avail_w / paper_w_in, avail_h / paper_h_in)

        paper_w_px = paper_w_in * scale
        paper_h_px = paper_h_in * scale
        offset_x = (self.width() - paper_w_px) / 2
        offset_y = (self.height() - paper_h_px) / 2

        # Drop shadow
        shadow = QRectF(offset_x + 4, offset_y + 4, paper_w_px, paper_h_px)
        painter.fillRect(shadow, QColor(0, 0, 0, 40))

        # Paper
        paper_rect = QRectF(offset_x, offset_y, paper_w_px, paper_h_px)
        painter.fillRect(paper_rect, QColor("white"))
        painter.setPen(QPen(QColor("#888"), 1))
        painter.drawRect(paper_rect)

        # Margin guide
        margin_px = layout.margin_in * scale
        margin_rect = QRectF(
            offset_x + margin_px,
            offset_y + margin_px,
            paper_w_px - 2 * margin_px,
            paper_h_px - 2 * margin_px,
        )
        painter.setPen(QPen(QColor("#d0d0d0"), 1, Qt.PenStyle.DashLine))
        painter.drawRect(margin_rect)

        # Cells
        for cell in layout.cells:
            cx = offset_x + cell.x_in * scale
            cy = offset_y + cell.y_in * scale
            cw = cell.width_in * scale
            ch = cell.height_in * scale
            cell_rect = QRectF(cx, cy, cw, ch)

            if self._thumb is not None:
                thumb_to_draw = self._thumb
                if cell.rotated:
                    transform = thumb_to_draw.transformed(
                        # rotate 90
                        # build via QTransform
                        __import__("PyQt6.QtGui", fromlist=["QTransform"]).QTransform().rotate(90),
                        Qt.TransformationMode.SmoothTransformation,
                    )
                    painter.drawPixmap(cell_rect, transform, QRectF(transform.rect()))
                else:
                    painter.drawPixmap(
                        cell_rect, thumb_to_draw, QRectF(thumb_to_draw.rect())
                    )
            else:
                painter.fillRect(cell_rect, QColor("#cce5ff"))

            painter.setPen(QPen(QColor("#3a7"), 1.2))
            painter.drawRect(cell_rect)

        # Label
        painter.setPen(QColor("#333"))
        painter.drawText(
            int(offset_x),
            int(offset_y - 8),
            f"{layout.paper.name}  -  {layout.rows} x {layout.cols}  -  "
            f"cell {layout.cell_width_in:.2f} x {layout.cell_height_in:.2f} in"
            f"{'  (rotated)' if layout.source_rotated else ''}",
        )
