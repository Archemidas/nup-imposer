"""ICC color management built on PIL.ImageCms (lcms2).

This module provides:
- Discovery of installed ICC profiles on Windows/macOS/Linux.
- Source-to-destination ICC transforms with rendering intent + BPC.
- Soft-proofing that simulates a printer profile on screen.

The lcms2 engine ships with Pillow, so no extra runtime dependency is required.
"""
from __future__ import annotations

import io
import sys
from dataclasses import dataclass, field
from enum import IntEnum
from functools import lru_cache
from pathlib import Path
from typing import List, Optional, Tuple, Union

from PIL import Image, ImageCms

ProfileSource = Union[bytes, Path, str, "ImageCms.ImageCmsProfile"]


class RenderingIntent(IntEnum):
    """ICC rendering intents (values match lcms2 / ICC v4 spec)."""

    PERCEPTUAL = 0
    RELATIVE_COLORIMETRIC = 1
    SATURATION = 2
    ABSOLUTE_COLORIMETRIC = 3

    @property
    def label(self) -> str:
        return {
            RenderingIntent.PERCEPTUAL: "Perceptual",
            RenderingIntent.RELATIVE_COLORIMETRIC: "Relative Colorimetric",
            RenderingIntent.SATURATION: "Saturation",
            RenderingIntent.ABSOLUTE_COLORIMETRIC: "Absolute Colorimetric",
        }[self]

    @classmethod
    def from_label(cls, text: str) -> "RenderingIntent":
        for member in cls:
            if member.label.lower() == text.lower():
                return member
        # Allow shorthand
        shorthand = {
            "perceptual": cls.PERCEPTUAL,
            "relative": cls.RELATIVE_COLORIMETRIC,
            "saturation": cls.SATURATION,
            "absolute": cls.ABSOLUTE_COLORIMETRIC,
        }
        if text.lower() in shorthand:
            return shorthand[text.lower()]
        raise ValueError(f"Unknown rendering intent: {text!r}")


@dataclass
class ProfileInfo:
    """Lightweight summary of an ICC profile on disk."""

    path: Path
    name: str
    color_space: str  # 'RGB', 'CMYK', 'GRAY', 'LAB', ...
    device_class: str  # 'mntr' (display), 'prtr' (printer), 'scnr' (scanner), ...

    @property
    def is_printer(self) -> bool:
        return self.device_class.lower().startswith("prtr")

    @property
    def is_display(self) -> bool:
        return self.device_class.lower().startswith("mntr")

    def __str__(self) -> str:
        return f"{self.name} [{self.color_space}]"


@dataclass
class ColorSettings:
    """User-facing color management state, shared between GUI and exporters."""

    dest_profile_path: Optional[Path] = None
    dest_profile_bytes: Optional[bytes] = None
    intent: RenderingIntent = RenderingIntent.PERCEPTUAL
    black_point_compensation: bool = True
    soft_proof_enabled: bool = False
    proof_intent: RenderingIntent = RenderingIntent.RELATIVE_COLORIMETRIC
    gamut_check: bool = False

    def has_destination(self) -> bool:
        return self.dest_profile_path is not None or self.dest_profile_bytes is not None

    def dest_source(self) -> Optional[ProfileSource]:
        """Return whichever form of the destination profile is set, or None."""
        if self.dest_profile_bytes is not None:
            return self.dest_profile_bytes
        if self.dest_profile_path is not None:
            return self.dest_profile_path
        return None


# ---------------------------------------------------------------------------
# Profile discovery
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def system_profile_dirs() -> Tuple[Path, ...]:
    """Return existing platform-standard ICC profile directories."""
    if sys.platform.startswith("win"):
        candidates = [Path(r"C:\Windows\System32\spool\drivers\color")]
    elif sys.platform == "darwin":
        candidates = [
            Path("/Library/ColorSync/Profiles"),
            Path("/System/Library/ColorSync/Profiles"),
            Path.home() / "Library/ColorSync/Profiles",
        ]
    else:
        candidates = [
            Path("/usr/share/color/icc"),
            Path("/var/lib/colord/icc"),
            Path.home() / ".local/share/icc",
            Path.home() / ".color/icc",
        ]
    return tuple(d for d in candidates if d.is_dir())


def list_installed_profiles(extra_dirs: Optional[List[Path]] = None) -> List[ProfileInfo]:
    """Return all readable ICC profiles in system dirs (+ any extras)."""
    seen: set = set()
    found: List[ProfileInfo] = []
    search = list(system_profile_dirs())
    if extra_dirs:
        search.extend(extra_dirs)
    for d in search:
        for path in Path(d).rglob("*"):
            if path.suffix.lower() not in (".icc", ".icm"):
                continue
            if path in seen:
                continue
            seen.add(path)
            try:
                found.append(read_profile_info(path))
            except Exception:
                continue
    return sorted(found, key=lambda p: p.name.lower())


def read_profile_info(path: Path) -> ProfileInfo:
    """Read header info for an ICC profile."""
    profile = ImageCms.getOpenProfile(str(path))
    try:
        name = ImageCms.getProfileDescription(profile).strip()
    except Exception:
        name = ""
    if not name:
        name = path.stem
    # Pillow exposes lcms2 profile header fields under profile.profile.* in recent versions
    cs = "RGB"
    klass = "unknown"
    try:
        cs = profile.profile.xcolor_space.strip()
    except Exception:
        pass
    try:
        klass = profile.profile.device_class.strip()
    except Exception:
        pass
    return ProfileInfo(path=Path(path), name=name, color_space=cs, device_class=klass)


# ---------------------------------------------------------------------------
# Profile loading helpers
# ---------------------------------------------------------------------------

def srgb_profile() -> "ImageCms.ImageCmsProfile":
    """Return a freshly-built built-in sRGB profile (wrapped)."""
    return ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB"))


def srgb_profile_bytes() -> bytes:
    """Return the sRGB profile as ICC bytes, suitable for embedding."""
    return srgb_profile().tobytes()


def _open(profile: ProfileSource) -> "ImageCms.ImageCmsProfile":
    if isinstance(profile, ImageCms.ImageCmsProfile):
        return profile
    if isinstance(profile, (bytes, bytearray)):
        return ImageCms.getOpenProfile(io.BytesIO(bytes(profile)))
    if isinstance(profile, (str, Path)):
        return ImageCms.getOpenProfile(str(profile))
    # Fall back to wrapping a raw CmsProfile core object if Pillow handed us one
    if hasattr(profile, "tobytes") and hasattr(profile, "profile"):
        return profile  # already wrapped
    try:
        return ImageCms.ImageCmsProfile(profile)
    except Exception as e:
        raise TypeError(f"Unsupported profile source: {type(profile).__name__}") from e


def _profile_color_space(profile: "ImageCms.ImageCmsProfile", default: str = "RGB") -> str:
    """Best-effort mapping from profile header to a PIL image mode."""
    try:
        cs = profile.profile.xcolor_space.strip()
    except Exception:
        return default
    return {
        "RGB": "RGB",
        "GRAY": "L",
        "CMYK": "CMYK",
        "LAB": "LAB",
    }.get(cs.upper(), default)


def ensure_source_profile(
    embedded_icc: Optional[bytes],
    image_mode: str,
) -> ProfileSource:
    """If the image has no embedded profile, return a sensible default.

    RGB / RGBA / L sources default to sRGB. CMYK is left to the caller -
    we still return sRGB here, but exporters should generally require an
    explicit source profile for CMYK input.
    """
    if embedded_icc:
        return embedded_icc
    return srgb_profile()


# ---------------------------------------------------------------------------
# Flag helpers (kept tolerant of Pillow API drift)
# ---------------------------------------------------------------------------

def _flag(name: str, fallback: int) -> int:
    """Resolve an ImageCms flag by name across Pillow versions."""
    flags = getattr(ImageCms, "Flags", None)
    if flags is not None:
        member = getattr(flags, name, None)
        if member is not None:
            return int(member)
    legacy = getattr(ImageCms, "FLAGS", None)
    if isinstance(legacy, dict) and name in legacy:
        return int(legacy[name])
    return fallback


_FLAG_BPC = _flag("BLACKPOINTCOMPENSATION", 0x2000)
_FLAG_SOFTPROOFING = _flag("SOFTPROOFING", 0x4000)
_FLAG_GAMUTCHECK = _flag("GAMUTCHECK", 0x1000)


# ---------------------------------------------------------------------------
# Transforms
# ---------------------------------------------------------------------------

def apply_transform(
    image: Image.Image,
    source_profile: ProfileSource,
    dest_profile: ProfileSource,
    intent: RenderingIntent = RenderingIntent.PERCEPTUAL,
    black_point_compensation: bool = True,
    output_mode: Optional[str] = None,
) -> Image.Image:
    """Convert pixels from source profile to destination profile.

    Returns a new PIL Image. The output mode follows the destination profile
    (RGB / CMYK / L / LAB) unless explicitly overridden.
    """
    src = _open(source_profile)
    dst = _open(dest_profile)
    out_mode = output_mode or _profile_color_space(dst)

    flags = 0
    if black_point_compensation:
        flags |= _FLAG_BPC

    transform = ImageCms.buildTransform(
        src, dst, image.mode, out_mode,
        renderingIntent=int(intent),
        flags=flags,
    )
    return ImageCms.applyTransform(image, transform)


def soft_proof(
    image: Image.Image,
    source_profile: ProfileSource,
    proof_profile: ProfileSource,
    display_profile: Optional[ProfileSource] = None,
    proof_intent: RenderingIntent = RenderingIntent.RELATIVE_COLORIMETRIC,
    display_intent: RenderingIntent = RenderingIntent.PERCEPTUAL,
    black_point_compensation: bool = True,
    gamut_check: bool = False,
) -> Image.Image:
    """Simulate how the image will look once converted through proof_profile
    and viewed on display_profile (defaults to sRGB).

    Output is always RGB and suitable for direct on-screen display.
    """
    src = _open(source_profile)
    proof = _open(proof_profile)
    display = _open(display_profile) if display_profile is not None else srgb_profile()

    flags = _FLAG_SOFTPROOFING
    if black_point_compensation:
        flags |= _FLAG_BPC
    if gamut_check:
        flags |= _FLAG_GAMUTCHECK

    transform = ImageCms.buildProofTransform(
        src, display, proof,
        image.mode, "RGB",
        renderingIntent=int(display_intent),
        proofRenderingIntent=int(proof_intent),
        flags=flags,
    )
    return ImageCms.applyTransform(image, transform)


def profile_bytes_from_source(source: ProfileSource) -> bytes:
    """Get the raw ICC bytes for a profile source (path / bytes / pre-opened)."""
    if isinstance(source, (bytes, bytearray)):
        return bytes(source)
    if isinstance(source, (str, Path)):
        with open(source, "rb") as f:
            return f.read()
    if isinstance(source, ImageCms.ImageCmsProfile):
        return source.tobytes()
    # Raw CmsProfile core object - wrap it
    try:
        return ImageCms.ImageCmsProfile(source).tobytes()
    except Exception as e:
        raise TypeError(f"Unsupported profile source: {type(source).__name__}") from e
