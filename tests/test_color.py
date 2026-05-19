"""Tests for ICC color management."""
from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image, ImageCms

from nup_imposer.core.color import (
    ColorSettings,
    RenderingIntent,
    apply_transform,
    ensure_source_profile,
    profile_bytes_from_source,
    soft_proof,
    srgb_profile,
    srgb_profile_bytes,
)


def _make_sample_image(mode: str = "RGB", size: tuple = (32, 32)) -> Image.Image:
    """Build a small image with a known color so we can verify transforms."""
    img = Image.new(mode, size, "red" if mode != "L" else 128)
    # Add a gradient so transforms have something interesting to do
    if mode in ("RGB", "RGBA"):
        for y in range(size[1]):
            for x in range(size[0]):
                img.putpixel((x, y), (x * 8 % 256, y * 8 % 256, 64))
    return img


def test_intent_labels_round_trip():
    for member in RenderingIntent:
        assert RenderingIntent.from_label(member.label) is member


def test_intent_shorthand():
    assert RenderingIntent.from_label("perceptual") is RenderingIntent.PERCEPTUAL
    assert RenderingIntent.from_label("relative") is RenderingIntent.RELATIVE_COLORIMETRIC
    assert RenderingIntent.from_label("saturation") is RenderingIntent.SATURATION
    assert RenderingIntent.from_label("absolute") is RenderingIntent.ABSOLUTE_COLORIMETRIC


def test_intent_rejects_unknown():
    with pytest.raises(ValueError):
        RenderingIntent.from_label("magical")


def test_srgb_profile_returns_valid_profile():
    profile = srgb_profile()
    assert profile is not None
    name = ImageCms.getProfileDescription(profile).strip()
    assert "srgb" in name.lower() or name  # any non-empty description is fine


def test_srgb_profile_bytes_returns_icc_bytes():
    data = srgb_profile_bytes()
    assert isinstance(data, (bytes, bytearray))
    assert len(data) > 100  # ICC profiles are at least a few hundred bytes


def test_srgb_to_srgb_transform_is_near_identity():
    img = _make_sample_image("RGB")
    profile_a = srgb_profile()
    profile_b = srgb_profile()
    out = apply_transform(img, profile_a, profile_b, RenderingIntent.PERCEPTUAL)
    assert out.mode == "RGB"
    assert out.size == img.size
    # Roundtrip should be very close (allow lcms2 a 1-step error per channel)
    diffs = []
    for y in range(0, img.height, 8):
        for x in range(0, img.width, 8):
            ip = img.getpixel((x, y))
            op = out.getpixel((x, y))
            diffs.extend(abs(a - b) for a, b in zip(ip, op))
    assert max(diffs) < 3, f"sRGB->sRGB drift too large: max={max(diffs)}"


def test_transform_accepts_bytes_profile():
    img = _make_sample_image("RGB")
    icc_bytes = srgb_profile_bytes()
    out = apply_transform(img, icc_bytes, icc_bytes, RenderingIntent.PERCEPTUAL)
    assert out.mode == "RGB"
    assert out.size == img.size


def test_soft_proof_returns_rgb():
    img = _make_sample_image("RGB")
    src = srgb_profile()
    # Use sRGB as the "proof" profile too - exercises the soft-proof pipeline
    out = soft_proof(img, src, src)
    assert out.mode == "RGB"
    assert out.size == img.size


def test_ensure_source_profile_falls_back_to_srgb():
    out = ensure_source_profile(None, "RGB")
    # Should be openable via ImageCms (either a profile object or bytes)
    bytes_form = profile_bytes_from_source(out)
    assert len(bytes_form) > 100


def test_ensure_source_profile_returns_embedded_when_present():
    icc_bytes = srgb_profile_bytes()
    out = ensure_source_profile(icc_bytes, "RGB")
    assert out is icc_bytes


def test_profile_bytes_from_path(tmp_path: Path):
    icc_bytes = srgb_profile_bytes()
    path = tmp_path / "test.icc"
    path.write_bytes(icc_bytes)
    out = profile_bytes_from_source(path)
    assert out == icc_bytes


def test_color_settings_defaults():
    s = ColorSettings()
    assert s.dest_profile_path is None
    assert s.dest_profile_bytes is None
    assert s.intent is RenderingIntent.PERCEPTUAL
    assert s.black_point_compensation is True
    assert s.soft_proof_enabled is False
    assert s.has_destination() is False
    assert s.dest_source() is None


def test_color_settings_with_path():
    s = ColorSettings(dest_profile_path=Path("/tmp/fake.icc"))
    assert s.has_destination() is True
    assert s.dest_source() == Path("/tmp/fake.icc")


def test_color_settings_with_bytes_takes_priority():
    s = ColorSettings(
        dest_profile_path=Path("/tmp/fake.icc"),
        dest_profile_bytes=b"icc-bytes-here",
    )
    assert s.dest_source() == b"icc-bytes-here"
