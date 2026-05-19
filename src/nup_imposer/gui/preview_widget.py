"""Live layout preview widget with soft-proof support."""
from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QColor, QPainter, QPen, QPixmap, QTransform
from PyQt6.QtWidgets import QWidget

from ..core.color import ColorSettings, ensure_source_profile, soft_proof
from ..core.image_loader import LoadedImage
from ..core.imposition import ImpositionLayout


class PreviewWidget(QWidget):
    """Renders the imposition layout to scale, with image thumbnails in cells.

    When the user enables soft-proof in the Color Management group, the
    thumbnail is run through `core.color.soft_proof` so the preview reflects
    the destination profile's likely appearance on screen.
    """

    THUMB_SIZE = 600  # max edge in pixels - big enough for a generous preview

    def __init__(self) -> None:
        super().__init__()
        self.setMinimumSize(420, 540)
        self._layout: Optional[ImpositionLayout] = None
        self._thumb: Optional[QPixmap] = None
        self._color_settings_signature: Optional[tuple] = None
        self.setStyleSheet("background: #f0f0f0;")

    def set_layout(
        self,
        layout: ImpositionLayout,
        image: LoadedImage,
        color_settings: Optional[ColorSettings] = None,
    ) -> None:
        self._layout = layout
        self._thumb = self._build_thumbnail(image, color_settings)
        self.update()

    def _build_thumbnail(
        self,
        image: LoadedImage,
        color_settings: Optional[ColorSettings],
    ) -> Optional[QPixmap]:
        """Build a (possibly soft-proofed) thumbnail of the source image."""
        try:
            from PIL.ImageQt import ImageQt
        except Exception:
            return None

        pil_thumb = image.pil_image.copy()
        pil_thumb.thumbnail((self.THUMB_SIZE, self.THUMB_SIZE))

        # Apply soft-proof if enabled and we have a destination
        if (
            color_settings is not None
            and color_settings.soft_proof_enabled
            and color_settings.has_destination()
        ):
            try:
                source = ensure_source_profile(image.icc_profile, pil_thumb.mode)
                pil_thumb = soft_proof(
                    pil_thumb,
                    source_profile=source,
                    proof_profile=color_settings.dest_source(),
                    proof_intent=color_settings.proof_intent,
                    display_intent=color_settings.intent,
                    black_point_compensation=color_settings.black_point_compensation,
                    gamut_check=color_settings.gamut_check,
                )
            except Exception:
                # Soft-proof failed - fall back to plain thumbnail
                pass

        if pil_thumb.mode == "CMYK":
            pil_thumb = pil_thumb.convert("RGB")
        elif pil_thumb.mode not in ("RGB", "RGBA"):
            pil_thumb = pil_thumb.convert("RGB")

        try:
            qim = ImageQt(pil_thumb)
            return QPixmap.fromImage(qim)
        except Exception:
            return None

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt convention
        painter = QPainter(self)
        painter.setRenderHints(
            QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform
        )

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

        pad = 36.0
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
                pix = self._thumb
                if cell.rotated:
                    pix = pix.transformed(
                        QTransform().rotate(90),
                        Qt.TransformationMode.SmoothTransformation,
                    )
                painter.drawPixmap(cell_rect, pix, QRectF(pix.rect()))
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
