"""Tests for paper size definitions."""
from nup_imposer.core.paper_sizes import (
    PAPER_SIZES,
    custom_paper_size,
    get_paper_size,
    US_LETTER,
)


def test_letter_size():
    assert US_LETTER.width_in == 8.5
    assert US_LETTER.height_in == 11.0


def test_to_pixels():
    w, h = US_LETTER.to_pixels(300)
    assert w == 2550
    assert h == 3300


def test_lookup():
    assert get_paper_size("Letter") is US_LETTER
    assert get_paper_size("Nonexistent") is None


def test_custom():
    p = custom_paper_size(5.0, 7.0)
    assert p.width_in == 5.0
    assert p.height_in == 7.0


def test_presets_present():
    expected = {"Letter", "Legal", "Tabloid (11x17)", "Super B (13x19)", "A4", "A3", "A3+"}
    assert expected <= set(PAPER_SIZES.keys())
