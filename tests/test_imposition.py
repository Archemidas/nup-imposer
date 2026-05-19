"""Tests for layout computation."""
import pytest

from nup_imposer.core.imposition import compute_layout
from nup_imposer.core.paper_sizes import US_LETTER, PHOTO_4X6


def test_4up_letter_square_source():
    layout = compute_layout(US_LETTER, n=4, source_aspect=1.0)
    assert layout.total_cells == 4
    assert layout.rows == 2 and layout.cols == 2
    assert len(layout.cells) == 4


def test_2up_landscape_source_on_letter():
    layout = compute_layout(US_LETTER, n=2, source_aspect=1.5)
    assert layout.total_cells == 2
    assert len(layout.cells) == 2


def test_9up_square():
    layout = compute_layout(US_LETTER, n=9, source_aspect=1.0)
    assert layout.rows * layout.cols >= 9


def test_rejects_zero_n():
    with pytest.raises(ValueError):
        compute_layout(US_LETTER, n=0, source_aspect=1.0)


def test_rejects_negative_aspect():
    with pytest.raises(ValueError):
        compute_layout(US_LETTER, n=2, source_aspect=-1.0)


def test_4up_4x6_photo():
    layout = compute_layout(PHOTO_4X6, n=4, source_aspect=1.5, margin_in=0.1, gutter_in=0.05)
    assert layout.total_cells == 4
    assert layout.cell_width_in > 0 and layout.cell_height_in > 0
