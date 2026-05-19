"""N-up imposition layout calculation.

Given a target paper size, source image aspect ratio, and N, find the best
grid arrangement (rows x cols) that maximizes cell area, accounting for
margins and gutters.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .paper_sizes import PaperSize


@dataclass
class CellPlacement:
    """The position and size of one imposed cell, all in inches."""
    x_in: float
    y_in: float
    width_in: float
    height_in: float
    rotated: bool = False  # True if source should be rotated 90 degrees


@dataclass
class ImpositionLayout:
    """The result of a layout calculation."""
    paper: PaperSize
    n: int
    rows: int
    cols: int
    margin_in: float
    gutter_in: float
    cell_width_in: float
    cell_height_in: float
    cells: list[CellPlacement] = field(default_factory=list)
    source_rotated: bool = False

    @property
    def total_cells(self) -> int:
        return self.rows * self.cols

    @property
    def cell_aspect(self) -> float:
        return self.cell_width_in / self.cell_height_in

    def usable_area_in(self) -> tuple[float, float]:
        """Area inside margins, in inches."""
        return (
            self.paper.width_in - 2 * self.margin_in,
            self.paper.height_in - 2 * self.margin_in,
        )


def _factor_pairs(n: int) -> list[tuple[int, int]]:
    """Return all (rows, cols) factor pairs of n, biased toward squareness."""
    pairs: list[tuple[int, int]] = []
    for r in range(1, n + 1):
        if n % r == 0:
            c = n // r
            pairs.append((r, c))
    # Also include "imperfect" arrangements where rows*cols >= n (handles primes nicely)
    # Example: 3-up on landscape paper - 1x3 strip is usually right, but 2x2 with one
    # empty slot can be better when the source is tall.
    for r in range(1, n + 1):
        for c in range(1, n + 1):
            if r * c >= n and r * c <= n + max(2, n // 2):
                if (r, c) not in pairs:
                    pairs.append((r, c))
    return pairs


def _cell_size(
    paper_w: float,
    paper_h: float,
    rows: int,
    cols: int,
    margin: float,
    gutter: float,
) -> tuple[float, float]:
    """Compute cell width and height in inches for a rows x cols grid."""
    usable_w = paper_w - 2 * margin - (cols - 1) * gutter
    usable_h = paper_h - 2 * margin - (rows - 1) * gutter
    if usable_w <= 0 or usable_h <= 0:
        return (0.0, 0.0)
    return (usable_w / cols, usable_h / rows)


def _fit_score(
    cell_w: float,
    cell_h: float,
    src_aspect: float,
) -> tuple[float, bool]:
    """How much of the cell does the source image fill, and should it be rotated?

    Returns (filled_area_fraction, rotated).
    """
    if cell_w <= 0 or cell_h <= 0:
        return (0.0, False)
    cell_aspect = cell_w / cell_h

    # Option 1: source not rotated (src_aspect = w/h of source)
    if src_aspect >= cell_aspect:
        # Source wider than cell - fit to width
        fit_w_a = cell_w
        fit_h_a = cell_w / src_aspect
    else:
        fit_h_a = cell_h
        fit_w_a = cell_h * src_aspect
    area_a = fit_w_a * fit_h_a

    # Option 2: rotated 90 degrees (aspect becomes 1/src_aspect)
    rot_aspect = 1.0 / src_aspect
    if rot_aspect >= cell_aspect:
        fit_w_b = cell_w
        fit_h_b = cell_w / rot_aspect
    else:
        fit_h_b = cell_h
        fit_w_b = cell_h * rot_aspect
    area_b = fit_w_b * fit_h_b

    if area_b > area_a:
        return (area_b / (cell_w * cell_h), True)
    return (area_a / (cell_w * cell_h), False)


def compute_layout(
    paper: PaperSize,
    n: int,
    source_aspect: float,
    margin_in: float = 0.25,
    gutter_in: float = 0.125,
    paper_orientation: Optional[str] = None,
) -> ImpositionLayout:
    """Find the best N-up arrangement on the given paper.

    Args:
        paper: Target paper size.
        n: Number of copies to fit.
        source_aspect: Width/height ratio of source image.
        margin_in: Margin on all sides, in inches.
        gutter_in: Gap between cells, in inches.
        paper_orientation: 'portrait', 'landscape', or None (try both, pick best).

    Returns:
        ImpositionLayout describing the optimal arrangement.
    """
    if n < 1:
        raise ValueError("n must be at least 1")
    if source_aspect <= 0:
        raise ValueError("source_aspect must be positive")

    # Decide which paper orientations to try
    if paper_orientation == "portrait":
        orientations = [(paper.width_in, paper.height_in)]
    elif paper_orientation == "landscape":
        orientations = [(paper.height_in, paper.width_in)]
    else:
        orientations = [
            (paper.width_in, paper.height_in),
            (paper.height_in, paper.width_in),
        ]

    best: Optional[ImpositionLayout] = None
    best_score = -1.0

    for paper_w, paper_h in orientations:
        for rows, cols in _factor_pairs(n):
            cell_w, cell_h = _cell_size(paper_w, paper_h, rows, cols, margin_in, gutter_in)
            if cell_w <= 0 or cell_h <= 0:
                continue
            fill_frac, rotated = _fit_score(cell_w, cell_h, source_aspect)
            # Prefer arrangements where the grid actually uses n cells
            grid_eff = n / (rows * cols)
            score = fill_frac * grid_eff
            if score > best_score:
                best_score = score
                # Use this orientation's paper dims
                oriented_paper = PaperSize(
                    paper.name + (" (L)" if paper_w > paper.width_in else ""),
                    paper_w,
                    paper_h,
                )
                cells = _place_cells(
                    paper_w, paper_h, rows, cols, margin_in, gutter_in,
                    cell_w, cell_h, rotated, source_aspect, n,
                )
                best = ImpositionLayout(
                    paper=oriented_paper,
                    n=n,
                    rows=rows,
                    cols=cols,
                    margin_in=margin_in,
                    gutter_in=gutter_in,
                    cell_width_in=cell_w,
                    cell_height_in=cell_h,
                    cells=cells,
                    source_rotated=rotated,
                )

    if best is None:
        raise RuntimeError("No valid layout found - try smaller margins or different paper")
    return best


def _place_cells(
    paper_w: float,
    paper_h: float,
    rows: int,
    cols: int,
    margin: float,
    gutter: float,
    cell_w: float,
    cell_h: float,
    rotated: bool,
    src_aspect: float,
    n: int,
) -> list[CellPlacement]:
    """Compute the exact placement of each cell's image within the grid."""
    cells: list[CellPlacement] = []
    src_aspect_effective = (1.0 / src_aspect) if rotated else src_aspect

    # Fit image to cell preserving aspect
    if src_aspect_effective >= cell_w / cell_h:
        img_w = cell_w
        img_h = cell_w / src_aspect_effective
    else:
        img_h = cell_h
        img_w = cell_h * src_aspect_effective

    placed = 0
    for r in range(rows):
        for c in range(cols):
            if placed >= n:
                break
            cell_x = margin + c * (cell_w + gutter)
            cell_y = margin + r * (cell_h + gutter)
            # Center image within cell
            x = cell_x + (cell_w - img_w) / 2
            y = cell_y + (cell_h - img_h) / 2
            cells.append(CellPlacement(
                x_in=x,
                y_in=y,
                width_in=img_w,
                height_in=img_h,
                rotated=rotated,
            ))
            placed += 1
        if placed >= n:
            break
    return cells
