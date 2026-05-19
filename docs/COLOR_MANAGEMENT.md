# Color Management

As of **0.2.0**, Nup Imposer ships with active ICC color management built on
PIL.ImageCms (lcms2). This document covers what's implemented today, how to
use it, and what's still on the roadmap.

## What's implemented (0.2.0)

### Profile discovery

`core.color.list_installed_profiles()` scans platform-standard folders:

| Platform | Searched paths |
|---|---|
| Windows | `C:\Windows\System32\spool\drivers\color` |
| macOS | `/Library/ColorSync/Profiles`, `/System/Library/ColorSync/Profiles`, `~/Library/ColorSync/Profiles` |
| Linux | `/usr/share/color/icc`, `/var/lib/colord/icc`, `~/.local/share/icc`, `~/.color/icc` |

Each profile is parsed for description, color space (RGB / CMYK / Gray / Lab),
and device class (`mntr`, `prtr`, `scnr`...). The GUI shows them in the
destination dropdown after pressing **Scan installed profiles**.

### Active transforms

```python
from nup_imposer.core.color import apply_transform, RenderingIntent

result = apply_transform(
    image,                      # PIL Image
    source_profile=embedded,    # bytes / path / ImageCmsProfile
    dest_profile=printer_path,
    intent=RenderingIntent.PERCEPTUAL,
    black_point_compensation=True,
)
```

Available rendering intents (matching the ICC spec):

- **Perceptual** - compresses the entire source gamut into destination gamut.
  Best for photographs.
- **Relative Colorimetric** - maps source white to destination white, clips
  out-of-gamut colors. Best for proofing and most fine-art workflows.
- **Saturation** - preserves vividness over accuracy. Useful for charts /
  business graphics.
- **Absolute Colorimetric** - preserves the source white point (no white-point
  mapping). For matching specific paper colors in proofing.

Black point compensation is on by default and matches Adobe's defaults.

### Soft-proofing

`core.color.soft_proof` runs the source image through the destination profile
and back to a display profile (defaults to sRGB) so you can preview how it
will print:

```python
from nup_imposer.core.color import soft_proof, RenderingIntent

preview = soft_proof(
    image,
    source_profile=embedded,
    proof_profile=printer_path,
    display_profile=None,                  # defaults to sRGB
    proof_intent=RenderingIntent.RELATIVE_COLORIMETRIC,
    display_intent=RenderingIntent.PERCEPTUAL,
    black_point_compensation=True,
    gamut_check=False,                     # set True for out-of-gamut overlay
)
```

In the GUI, check **Soft-proof preview** in the Color Management group. The
preview canvas re-renders through this pipeline. Toggle **Gamut warning** to
overlay an out-of-gamut indicator.

### Exporter integration

Both `export_tiff` and `export_pdf` accept either explicit color args or a
`ColorSettings` bundle:

```python
from nup_imposer.core import export_tiff, ColorSettings, RenderingIntent

settings = ColorSettings(
    dest_profile_path=Path("Pro9500_Glossy.icc"),
    intent=RenderingIntent.PERCEPTUAL,
    black_point_compensation=True,
)
export_tiff(image, layout, "out.tif", output_dpi=300, color_settings=settings)
```

When a destination profile is set, the output's ICC tag is **replaced** with
the destination profile's bytes so the file's pixel data and ICC tag agree.

### CLI

```bash
python -m nup_imposer photo.jpg -n 4 -p Letter \
    --dest-profile path/to/Profile.icc \
    --intent perceptual          # or relative / saturation / absolute
    # --no-bpc to disable BPC
```

## Sources of profiles

- **Manufacturer profiles** - Epson, Canon, HP, and paper makers (Hahnemuhle,
  Canson, Red River, etc.) all ship ICC profiles for specific printer + paper +
  ink combinations. Drop them into the OS profile folder and they'll appear
  in the dropdown after a rescan.
- **System profiles** - Windows, macOS, and Linux ship a starter set.
- **Custom profiles** - the Browse... entry in the dropdown takes any
  `.icc` / `.icm` file.

## What's still on the roadmap

### 0.3.x - target presets

One-click conversions backed by a registry of common printer + paper + ink combos:

| From | To | Use case |
|---|---|---|
| sRGB | Generic CMYK SWOP | Commercial print |
| sRGB / AdobeRGB | Epson Artisan 1400 + glossy photo | Home photo |
| AdobeRGB | Canon Pixma Pro9500 II + matte fine art | Fine art |
| sRGB | Sublimation transfer paper | Heat-press workflow |

### 0.4.x - multi-ink RIP-ready output

Consumer printers with 6+ inks (Epson Artisan 1400 = 6-color CMYK+Cl+Ml;
Canon Pixma Pro9500 Mark II = 10-color including light grays and red/green)
still take RGB/CMYK from the OS driver - **direct multi-ink output needs a
RIP** (ColorBurst, Wasatch, Mirage, ErgoSoft, Print-Factory).

What Nup Imposer 0.4.x will add for that workflow:

1. **Profile registry per printer/paper/ink** so users pick "Pro9500 II +
   Photo Paper Pro Platinum + PGI-9 inks" and the right ICC is loaded.
2. **Multi-channel TIFF output** - DeviceN / spot-channel TIFF that a RIP can
   ingest directly.
3. **Sublimation mode** - auto-mirror, sub-paper profile, correct intent
   (typically Relative Colorimetric), BPC defaults that match sub workflows.

### 0.5.x - quality checks

- **Gamut warning overlay** (basic version already in 0.2.0 - this will get a
  proper highlight color and per-pixel statistics).
- **Ink coverage estimate** (TAC) for CMYK output with paper-limit warnings.

## What this app intentionally won't do

- **Generate ICC profiles from scratch.** Profile creation needs a
  spectrophotometer (X-Rite i1Pro, ColorMunki, ColorChecker Studio) and
  dedicated software (i1Profiler, Argyll CMS). Nup Imposer consumes profiles,
  it does not create them.
- **Replace a RIP.** RIPs do screening, halftoning, ink limiting, dot-gain
  curves, and direct multi-channel output. Nup Imposer prepares correctly
  color-managed source files; the RIP handles output.
