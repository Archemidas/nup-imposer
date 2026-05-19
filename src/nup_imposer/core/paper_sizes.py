"""Paper size definitions.

All dimensions are in inches, given as (width, height) in portrait orientation.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Tuple


@dataclass(frozen=True)
class PaperSize:
    """A paper size in inches."""
    name: str
    width_in: float
    height_in: float

    @property
    def aspect(self) -> float:
        return self.width_in / self.height_in

    def to_pixels(self, dpi: int) -> Tuple[int, int]:
        """Convert physical dimensions to pixel dimensions at given DPI."""
        return (int(round(self.width_in * dpi)), int(round(self.height_in * dpi)))


# Common US paper sizes
US_LETTER = PaperSize("Letter", 8.5, 11.0)
US_LEGAL = PaperSize("Legal", 8.5, 14.0)
US_TABLOID = PaperSize("Tabloid (11x17)", 11.0, 17.0)
US_SUPER_B = PaperSize("Super B (13x19)", 13.0, 19.0)

# ISO A-series
A6 = PaperSize("A6", 4.13, 5.83)
A5 = PaperSize("A5", 5.83, 8.27)
A4 = PaperSize("A4", 8.27, 11.69)
A3 = PaperSize("A3", 11.69, 16.54)
A3_PLUS = PaperSize("A3+", 13.0, 19.0)
A2 = PaperSize("A2", 16.54, 23.39)

# Photo print sizes
PHOTO_4X6 = PaperSize("4x6 Photo", 4.0, 6.0)
PHOTO_5X7 = PaperSize("5x7 Photo", 5.0, 7.0)
PHOTO_8X10 = PaperSize("8x10 Photo", 8.0, 10.0)
PHOTO_8X12 = PaperSize("8x12 Photo", 8.0, 12.0)
PHOTO_11X14 = PaperSize("11x14 Photo", 11.0, 14.0)

# Sublimation common
SUB_MUG_WRAP = PaperSize("Mug Wrap (9.5x4)", 9.5, 4.0)


PAPER_SIZES: Dict[str, PaperSize] = {
    p.name: p
    for p in [
        US_LETTER,
        US_LEGAL,
        US_TABLOID,
        US_SUPER_B,
        A6,
        A5,
        A4,
        A3,
        A3_PLUS,
        A2,
        PHOTO_4X6,
        PHOTO_5X7,
        PHOTO_8X10,
        PHOTO_8X12,
        PHOTO_11X14,
        SUB_MUG_WRAP,
    ]
}


def get_paper_size(name: str) -> Optional[PaperSize]:
    """Look up a preset paper size by name."""
    return PAPER_SIZES.get(name)


def custom_paper_size(width_in: float, height_in: float) -> PaperSize:
    """Create a custom paper size."""
    return PaperSize(f"Custom ({width_in}x{height_in})", width_in, height_in)
