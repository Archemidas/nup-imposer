"""Tests for core/tac.py — TAC estimation and channel splitting."""
from __future__ import annotations

import pytest
from PIL import Image

from nup_imposer.core.ink_channels import get_default_ink_registry
from nup_imposer.core.tac import TACResult, channel_split, estimate_tac, _split_channel_bytes


# ---------------------------------------------------------------------------
# TAC estimation
# ---------------------------------------------------------------------------

def _solid_cmyk(c: int, m: int, y: int, k: int, size=(10, 10)) -> Image.Image:
    """Create a solid CMYK image with the given channel values."""
    img = Image.new("CMYK", size, (c, m, y, k))
    return img


def test_tac_solid_zero():
    """A blank image (no ink) should return TAC ≈ 0."""
    img = _solid_cmyk(0, 0, 0, 0)
    result = estimate_tac(img, tac_limit=300.0)
    assert result.average_pct == pytest.approx(0.0, abs=0.1)
    assert result.max_pct == pytest.approx(0.0, abs=0.1)
    assert not result.exceeds_limit


def test_tac_solid_100k():
    """100% black = K=255, others 0. TAC should be ≈ 100%."""
    img = _solid_cmyk(0, 0, 0, 255)
    result = estimate_tac(img, tac_limit=300.0)
    assert result.average_pct == pytest.approx(100.0, abs=0.5)
    assert result.max_pct == pytest.approx(100.0, abs=0.5)
    assert not result.exceeds_limit


def test_tac_solid_400():
    """All channels at 255 → TAC = 400% (well over limit)."""
    img = _solid_cmyk(255, 255, 255, 255)
    result = estimate_tac(img, tac_limit=300.0)
    assert result.max_pct == pytest.approx(400.0, abs=0.5)
    assert result.exceeds_limit
    assert result.pixels_over == result.total_pixels


def test_tac_solid_300_at_limit():
    """TAC exactly equal to limit → should NOT exceed (limit is exclusive)."""
    # 300% ≈ each channel at 255 * 3/4 ≈ 191 → 255+255+255+0 = 765 raw
    # Let's use C=255, M=255, Y=255, K=0 → TAC = 300%
    img = _solid_cmyk(255, 255, 255, 0)
    result = estimate_tac(img, tac_limit=300.0)
    assert result.max_pct == pytest.approx(300.0, abs=0.5)
    assert not result.exceeds_limit


def test_tac_rgb_input():
    """RGB input is auto-converted to CMYK and produces a valid result."""
    img = Image.new("RGB", (20, 20), (128, 64, 64))
    result = estimate_tac(img, tac_limit=300.0)
    assert 0.0 <= result.average_pct <= 400.0
    assert result.total_pixels == 20 * 20


def test_tac_result_fraction_over():
    """fraction_over reflects proportion of over-limit pixels."""
    # Half the image over limit
    img = Image.new("CMYK", (10, 10), (0, 0, 0, 0))
    # Draw half the pixels with full ink
    half = Image.new("CMYK", (5, 10), (255, 255, 255, 255))
    img.paste(half, (0, 0))
    result = estimate_tac(img, tac_limit=300.0)
    assert result.fraction_over == pytest.approx(0.5, abs=0.05)


def test_tac_summary_contains_limit():
    img = _solid_cmyk(0, 0, 0, 0)
    result = estimate_tac(img, tac_limit=260.0)
    summary = result.summary()
    assert "260" in summary


def test_tac_summary_ok_message():
    img = _solid_cmyk(0, 0, 0, 0)
    result = estimate_tac(img, tac_limit=300.0)
    assert "OK" in result.summary() or "within" in result.summary()


def test_tac_summary_warning_when_exceeded():
    img = _solid_cmyk(255, 255, 255, 255)
    result = estimate_tac(img, tac_limit=300.0)
    assert "WARNING" in result.summary() or "exceed" in result.summary().lower()


def test_tac_p95_leq_max():
    """95th-percentile must always be ≤ maximum."""
    img = Image.new("CMYK", (50, 50))
    import random
    pixels = [(random.randint(0, 255),) * 4 for _ in range(50 * 50)]
    img.putdata(pixels)
    result = estimate_tac(img, tac_limit=300.0)
    assert result.p95_pct <= result.max_pct


# ---------------------------------------------------------------------------
# Channel split helpers
# ---------------------------------------------------------------------------

def test_split_channel_bytes_zero():
    raw = bytes([0] * 100)
    main, light = _split_channel_bytes(raw, 128)
    assert all(v == 255 for v in light), "0-value should give max light"
    assert all(v == 0 for v in main)


def test_split_channel_bytes_max():
    raw = bytes([255] * 100)
    main, light = _split_channel_bytes(raw, 128)
    assert all(v == 255 for v in main), "255-value should give max main"
    assert all(v == 0 for v in light)


def test_split_channel_bytes_at_threshold():
    raw = bytes([128])
    main, light = _split_channel_bytes(raw, 128)
    # At exactly the threshold: light = 0 (T - T = 0), main = 0 (T is not > T)
    assert light[0] == 0
    assert main[0] == 0


def test_split_channel_bytes_non_overlapping():
    """Main and light should not both be non-zero for the same pixel."""
    raw = bytes(range(256))
    main, light = _split_channel_bytes(raw, 128)
    for m, l in zip(main, light):
        assert not (m > 0 and l > 0), f"Overlap at pixel with main={m} light={l}"


# ---------------------------------------------------------------------------
# channel_split
# ---------------------------------------------------------------------------

def test_channel_split_4color():
    """Standard CMYK ink set → 4 channels matching the original."""
    registry = get_default_ink_registry()
    s = registry.find("cmyk_standard")
    assert s is not None

    img = _solid_cmyk(100, 80, 60, 40)
    channels = channel_split(img, s)
    assert len(channels) == 4
    for ch in channels:
        assert ch.mode == "L"
        assert ch.size == img.size


def test_channel_split_6color():
    """6-color ink set → 6 channel images."""
    registry = get_default_ink_registry()
    s = registry.find("epson_artisan_1400_6color")
    assert s is not None

    img = _solid_cmyk(200, 150, 100, 50)
    channels = channel_split(img, s)
    assert len(channels) == 6


def test_channel_split_returns_l_mode():
    """All returned channels must be in 'L' (8-bit grayscale) mode."""
    registry = get_default_ink_registry()
    s = registry.find("canon_pro9500ii_10color")
    assert s is not None
    img = _solid_cmyk(128, 128, 128, 128)
    channels = channel_split(img, s)
    for ch in channels:
        assert ch.mode == "L"


def test_channel_split_low_cyan_goes_to_light():
    """Low cyan values should produce non-zero light cyan and near-zero main cyan."""
    registry = get_default_ink_registry()
    s = registry.find("epson_artisan_1400_6color")
    assert s is not None

    # Very low cyan (10), zero everything else
    img = Image.new("CMYK", (5, 5), (10, 0, 0, 0))
    channels = channel_split(img, s)

    # Find C and LC channels by ink_set order
    c_idx = next(i for i, ch in enumerate(s.channels) if ch.abbreviation == "C")
    lc_idx = next(i for i, ch in enumerate(s.channels) if ch.abbreviation == "LC")

    c_val = channels[c_idx].getpixel((0, 0))
    lc_val = channels[lc_idx].getpixel((0, 0))

    assert c_val == 0, f"Main cyan should be 0 at low density, got {c_val}"
    assert lc_val > 0, f"Light cyan should be > 0 at low density, got {lc_val}"


def test_channel_split_high_cyan_goes_to_main():
    """High cyan values should produce non-zero main cyan and zero light cyan."""
    registry = get_default_ink_registry()
    s = registry.find("epson_artisan_1400_6color")
    assert s is not None

    img = Image.new("CMYK", (5, 5), (240, 0, 0, 0))
    channels = channel_split(img, s)

    c_idx = next(i for i, ch in enumerate(s.channels) if ch.abbreviation == "C")
    lc_idx = next(i for i, ch in enumerate(s.channels) if ch.abbreviation == "LC")

    c_val = channels[c_idx].getpixel((0, 0))
    lc_val = channels[lc_idx].getpixel((0, 0))

    assert c_val > 0, f"Main cyan should be > 0 at high density, got {c_val}"
    assert lc_val == 0, f"Light cyan should be 0 at high density, got {lc_val}"


def test_channel_split_rgb_input_converts():
    """channel_split accepts RGB images (auto-converts to CMYK)."""
    registry = get_default_ink_registry()
    s = registry.find("cmyk_standard")
    assert s is not None
    img = Image.new("RGB", (10, 10), (200, 150, 100))
    channels = channel_split(img, s)
    assert len(channels) == 4


def test_channel_split_10color():
    """10-color ink set produces 10 channels."""
    registry = get_default_ink_registry()
    s = registry.find("epson_p900_10color")
    assert s is not None
    img = _solid_cmyk(100, 100, 100, 100)
    channels = channel_split(img, s)
    assert len(channels) == 10
