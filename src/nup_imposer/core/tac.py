"""TAC (Total Area Coverage) estimation and channel splitting.

TAC is the sum of all ink channels as a percentage per pixel.  For CMYK:
  TAC = (C + M + Y + K) / 255 * 100   at each pixel (max 400%).

A TAC value exceeding the paper's absorption limit causes ink bleeding,
extended drying times, and colour shift.  estimate_tac() analyses the
composited image (after any ICC transform) and reports average, 95th-
percentile, and maximum TAC together with a count of over-limit pixels.

channel_split() derives the full N-channel image required for DeviceN TIFF
export.  For printers with light inks (Light Cyan, Light Magenta, etc.) it
applies a threshold split:

  - Values at or below split_at → mapped to the light channel
  - Values above split_at      → mapped to the main (dark) channel

This is a simplified model; real RIP ink optimisation uses the full printer
ICC profile plus GCR/UCR curves.  For TAC estimation and RIP-ingestion TIFF
the model is accurate enough to be actionable.
"""
from __future__ import annotations

import dataclasses
from typing import List, Optional, Tuple

from PIL import Image

from .ink_channels import InkChannel, InkSet


# ---------------------------------------------------------------------------
# TAC result
# ---------------------------------------------------------------------------

@dataclasses.dataclass
class TACResult:
    """Statistics from a TAC estimation pass."""

    tac_limit: float        # ink set's paper-specific limit (%)
    average_pct: float      # mean TAC across all sampled pixels (%)
    p95_pct: float          # 95th-percentile TAC (%)
    max_pct: float          # maximum per-pixel TAC (%)
    pixels_over: int        # count of pixels exceeding tac_limit
    total_pixels: int       # total sampled pixel count

    @property
    def fraction_over(self) -> float:
        """Fraction of pixels exceeding the TAC limit (0.0–1.0)."""
        if self.total_pixels == 0:
            return 0.0
        return self.pixels_over / self.total_pixels

    @property
    def exceeds_limit(self) -> bool:
        return self.max_pct > self.tac_limit

    def summary(self) -> str:
        """Return a human-readable multi-line summary."""
        lines = [
            f"TAC limit : {self.tac_limit:.0f}%",
            f"Average   : {self.average_pct:.1f}%",
            f"95th pct  : {self.p95_pct:.1f}%",
            f"Maximum   : {self.max_pct:.1f}%",
        ]
        if self.exceeds_limit:
            lines.append(
                f"⚠ WARNING: {self.pixels_over:,} of {self.total_pixels:,} pixels "
                f"({self.fraction_over * 100:.1f}%) exceed the {self.tac_limit:.0f}% limit."
            )
        else:
            lines.append("✓ All pixels within TAC limit.")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# TAC estimation
# ---------------------------------------------------------------------------

_MAX_SAMPLE_PIXELS = 1_000_000  # downsample above this to keep estimation fast


def estimate_tac(
    image: Image.Image,
    tac_limit: float = 300.0,
) -> TACResult:
    """Estimate TAC statistics for a PIL Image.

    The image is converted to CMYK (via Pillow's built-in conversion, which
    assumes sRGB input when no ICC transform has been applied) and analysed
    at up to 1 megapixel resolution for speed.

    For accurate results, apply an ICC colour transform to the composited
    canvas *before* calling this function.

    Args:
        image:      Any PIL Image (CMYK, RGB, L, …).
        tac_limit:  Paper-specific total ink limit in percentage (0–400).

    Returns:
        TACResult with average, p95, max, and over-limit pixel counts.
    """
    # --- Downsample for speed ---
    w, h = image.size
    if w * h > _MAX_SAMPLE_PIXELS:
        scale = (_MAX_SAMPLE_PIXELS / (w * h)) ** 0.5
        new_w = max(1, int(w * scale))
        new_h = max(1, int(h * scale))
        image = image.resize((new_w, new_h), Image.BILINEAR)

    # --- Convert to CMYK ---
    if image.mode == "CMYK":
        cmyk = image
    else:
        cmyk = image.convert("CMYK")

    # --- Per-channel bytes ---
    c_img, m_img, y_img, k_img = cmyk.split()
    c_bytes = c_img.tobytes()
    m_bytes = m_img.tobytes()
    y_bytes = y_img.tobytes()
    k_bytes = k_img.tobytes()
    n_pixels = len(c_bytes)

    # --- Histogram of TAC values (0–1020 raw; 4 × 255 max) ---
    hist = [0] * 1021
    for ci, mi, yi, ki in zip(c_bytes, m_bytes, y_bytes, k_bytes):
        hist[ci + mi + yi + ki] += 1

    # --- Aggregate stats from histogram ---
    total_raw = sum(v * hist[v] for v in range(1021))
    avg_raw = total_raw / n_pixels if n_pixels > 0 else 0.0

    max_raw = 0
    for v in range(1020, -1, -1):
        if hist[v] > 0:
            max_raw = v
            break

    limit_raw = int(tac_limit * 255.0 / 100.0)
    pixels_over = sum(hist[v] for v in range(limit_raw + 1, 1021))

    # 95th percentile (cumulative histogram walk)
    target = int(n_pixels * 0.95)
    cumsum = 0
    p95_raw = 0
    for v in range(1021):
        cumsum += hist[v]
        if cumsum >= target:
            p95_raw = v
            break

    scale = 100.0 / 255.0  # raw 0–255 per channel → percent
    return TACResult(
        tac_limit=tac_limit,
        average_pct=avg_raw * scale,
        p95_pct=p95_raw * scale,
        max_pct=max_raw * scale,
        pixels_over=pixels_over,
        total_pixels=n_pixels,
    )


# ---------------------------------------------------------------------------
# Channel splitting for multi-ink output
# ---------------------------------------------------------------------------

def _split_channel_bytes(
    raw_bytes: bytes,
    split_at: int,
) -> Tuple[bytes, bytes]:
    """Split one channel's bytes into (main, light) components.

    main  = 0 below split_at, then scales 0→255 above it.
    light = 255 at 0, then scales 255→0 down to split_at, 0 above it.

    The two channels are non-overlapping and together cover the full
    0–255 density range without doubling ink.
    """
    T = max(1, min(254, split_at))
    upper_range = max(1, 255 - T)
    lower_range = T

    main_bytes = bytearray(len(raw_bytes))
    light_bytes = bytearray(len(raw_bytes))

    for i, v in enumerate(raw_bytes):
        if v <= T:
            main_bytes[i] = 0
            light_bytes[i] = (T - v) * 255 // lower_range
        else:
            main_bytes[i] = (v - T) * 255 // upper_range
            light_bytes[i] = 0

    return bytes(main_bytes), bytes(light_bytes)


def channel_split(cmyk_image: Image.Image, ink_set: InkSet) -> List[Image.Image]:
    """Derive N channel images from a CMYK image for the given ink set.

    Returns one 'L' (8-bit grayscale) PIL Image per channel in the ink set's
    channel order.  Channels with no CMYK equivalent (e.g. Red, Green,
    Violet extension inks) are filled with zeros — the RIP handles gamut
    extension mapping from its ICC profile.

    For ink sets with light variants, the CMYK parent channel is split:
      - The main ink image replaces the original parent channel.
      - The light ink image carries the low-density complement.

    Args:
        cmyk_image: PIL Image, must be mode CMYK or will be converted.
        ink_set:    InkSet describing the target channel layout.

    Returns:
        List of PIL Image objects in mode 'L', len == ink_set.n_channels.
    """
    if cmyk_image.mode != "CMYK":
        cmyk_image = cmyk_image.convert("CMYK")

    c_img, m_img, y_img, k_img = cmyk_image.split()
    size = cmyk_image.size

    # Canonical CMYK source lookup
    raw: dict = {
        "C": c_img, "M": m_img, "Y": y_img, "K": k_img,
        # Map alternate abbreviations for printers that rename channels
        "VM": m_img,   # Vivid Magenta → use Magenta channel
        "BK": k_img,   # Black variants
        "MBK": k_img,
        "PBK": k_img,  # Photo Black — derived from K
    }

    # Build split cache: for each parent that has a light child, compute main/light pair
    # Multiple light channels from the same parent (e.g. LK + LLK from K) use different
    # split thresholds; we keep the highest split_at for the main split and compute
    # the secondary light from the residual.
    split_cache: dict = {}   # parent_abbr → (main_img, light_img)
    light_channels = [ch for ch in ink_set.channels if ch.is_light and ch.parent]

    # Group light channels by parent, sorted by split_at descending so the
    # highest split_at defines the boundary between main and first light.
    from collections import defaultdict
    parent_groups: dict = defaultdict(list)
    for ch in light_channels:
        parent_groups[ch.parent].append(ch)

    for parent_abbr, children in parent_groups.items():
        if parent_abbr not in raw:
            continue
        parent_img = raw[parent_abbr]
        parent_bytes = parent_img.tobytes()
        # Use the highest split_at child as the primary split point for main/light
        primary_split = max(ch.split_at for ch in children)
        main_b, light_b = _split_channel_bytes(parent_bytes, primary_split)
        main_img = Image.frombytes("L", size, main_b)
        light_img = Image.frombytes("L", size, light_b)
        split_cache[parent_abbr] = (main_img, light_img)

        # For secondary splits (e.g. LLK at 64 inside the LK region):
        # split the *light* portion further if there are multiple light children
        if len(children) > 1:
            children_sorted = sorted(children, key=lambda c: c.split_at, reverse=True)
            for i in range(1, len(children_sorted)):
                sub_split = children_sorted[i].split_at
                # Split the existing light image further
                existing_light_b = light_img.tobytes()
                _, sub_light_b = _split_channel_bytes(existing_light_b, sub_split)
                sub_key = f"{parent_abbr}__{i}"
                sub_light_img = Image.frombytes("L", size, sub_light_b)
                split_cache[sub_key] = (light_img, sub_light_img)

    # Build per-channel index for multi-light parents (LK/LLK from K)
    # Track which child index each light channel is for its parent
    parent_child_idx: dict = defaultdict(int)

    result: List[Image.Image] = []
    for ch in ink_set.channels:
        if not ch.is_light:
            # Main channel: use split main if the parent was split, else raw
            parent = ch.abbreviation
            if parent in split_cache:
                result.append(split_cache[parent][0])
            elif parent in raw:
                result.append(raw[parent])
            else:
                result.append(Image.new("L", size, 0))
        else:
            # Light channel
            parent = ch.parent or ""
            if parent not in split_cache:
                result.append(Image.new("L", size, 0))
                continue
            idx = parent_child_idx[parent]
            parent_child_idx[parent] += 1
            if idx == 0:
                result.append(split_cache[parent][1])
            else:
                sub_key = f"{parent}__{idx}"
                result.append(
                    split_cache[sub_key][1] if sub_key in split_cache
                    else Image.new("L", size, 0)
                )

    return result
