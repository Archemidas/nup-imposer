# Color Management Roadmap

This document captures the planned color-management pipeline. Phase 1 (the
current release) preserves embedded source ICC profiles only. Active CMS is
planned for 0.2.x and later.

## Today (0.1.x): preserve-only

- Source ICC is read on load.
- Source ICC is embedded on TIFF export.
- No transform happens between source and output - if your source is sRGB JPEG
  and you export TIFF, the output is still sRGB.
- Color mode is preserved end-to-end (RGB stays RGB, CMYK stays CMYK).

That's enough for most "just print this 4-up" workflows where the driver or RIP
does the final transform.

## 0.2.x: active ICC transforms

Goal: do the source-to-destination color conversion inside the app so the file
sent to the driver/RIP is already targeted.

```
LoadedImage (with source ICC)
       |
       v
+------+-------+
| color.py     |   wraps PIL.ImageCms (lcms2)
|   convert()  |
+------+-------+
       |
       v
Imposed canvas in destination color space
       |
       v
TIFF / PDF with destination ICC embedded
```

### Planned API

```python
from PIL import ImageCms

def transform_to_destination(
    pil_image,
    source_profile_bytes,
    destination_profile_path,
    rendering_intent="perceptual",  # or "relative_colorimetric", "saturation", "absolute_colorimetric"
    bpc=True,  # black point compensation
):
    src = ImageCms.ImageCmsProfile(io.BytesIO(source_profile_bytes))
    dst = ImageCms.ImageCmsProfile(destination_profile_path)
    transform = ImageCms.buildTransform(
        src, dst, pil_image.mode, "CMYK" if "Cmyk" in str(dst) else "RGB",
        renderingIntent=_intent_map[rendering_intent],
        flags=ImageCms.Flags.BLACKPOINTCOMPENSATION if bpc else 0,
    )
    return ImageCms.applyTransform(pil_image, transform)
```

### Profile sources

- **Manufacturer profiles**: Epson, Canon, HP, and most paper makers ship ICC
  profiles for specific printer + paper + ink combinations. Drop them into a
  user profiles folder; the app indexes by filename.
- **System profiles**: Windows stores installed ICCs in
  `C:\Windows\System32\spool\drivers\color\`. The app can read from here too.
- **Custom profiles**: users can browse to any `.icc` / `.icm` file.

### GUI additions

A new "Color Management" group will appear:

- Source profile: detected/embedded (read-only) or override
- Destination profile: dropdown of installed profiles + Browse
- Rendering intent: Perceptual / Relative Colorimetric / Saturation / Absolute
- Black point compensation: checkbox
- Soft-proof preview: toggle that re-renders the preview through the destination
  profile so on-screen colors approximate the printed result

## 0.3.x: source-class -> destination-class shortcuts

Common conversions get one-click presets:

| From | To | Use case |
|---|---|---|
| sRGB | Generic CMYK SWOP | Send to commercial print |
| sRGB / AdobeRGB | Epson Artisan 1400 + glossy photo | Home photo printing |
| AdobeRGB | Canon Pixma Pro9500 II + matte fine art | Fine art |
| sRGB | Sublimation transfer paper (e.g. TexPrint) | Sublimation workflow |

## 0.4.x: multi-ink / RIP-aware output

Consumer printers with more than 4 inks (Epson Artisan 1400 = 6-color C,M,Y,K,Cl,Ml;
Canon Pixma Pro9500 Mark II = 10-color including light grays, photo cyan/magenta,
and red/green) still take RGB or CMYK from the OS driver - the driver linearizes
into its ink set internally. **Direct multi-ink output to those printers requires
a third-party RIP** (ColorBurst, Wasatch, Mirage, Print-Factory, ErgoSoft).

What Nup Imposer can do well here:

1. **Profile registry per printer + paper + ink**. Build a JSON catalog so users
   pick "Pro9500 II + Canon Photo Paper Pro Platinum + PGI-9 inks" and the right
   ICC is selected automatically.
2. **Multi-channel TIFF output**. Pillow can write multi-channel TIFF; we'd
   extend `exporters.py` to write a DeviceN / spot-channel TIFF that a RIP can
   ingest directly.
3. **Sublimation defaults**: auto-mirror the canvas, force the sublimation-specific
   working profile, embed the heat-press profile, set the correct rendering
   intent (typically Relative Colorimetric for sublimation).

### Sublimation specifics

Sublimation needs:

- Image mirrored horizontally (heat transfer flips it).
- A sublimation-paper / sublimation-ink / substrate-specific ICC profile.
- Often **black point compensation off** and **relative colorimetric** intent,
  because sub gamut tops out differently from photo paper.
- A specific output DPI - most sub workflows are 200-300 DPI.

We can ship a "Sublimation mode" toggle that applies these defaults and adds a
"mirror output" checkbox.

## 0.5.x: print previews

- **Gamut warning overlay**: highlight pixels that will be clipped by the
  destination profile.
- **Ink coverage estimate**: show total area coverage % for CMYK and warn if
  it exceeds the paper's recommended TAC (Total Area Coverage).

## Library choices

| Need | Library | License |
|---|---|---|
| Apply ICC transforms | PIL.ImageCms (lcms2 bindings) | MIT |
| Read ICC tag tables | `iccprofiles` or low-level `colour` package | BSD |
| Multi-channel TIFF | Pillow `save("CMYK", ...)` extended for N-channel | MIT |
| Spot color / DeviceN PDF | reportlab or PyMuPDF | LGPL/AGPL |

## What this app intentionally won't do

- **Generate ICC profiles from scratch.** Profile creation needs a
  spectrophotometer (X-Rite i1Pro, ColorMunki) and dedicated software (i1Profiler,
  Argyll CMS). Nup Imposer consumes profiles, it doesn't create them.
- **Replace a RIP.** RIPs do screening, halftoning, ink limiting, dot-gain
  curves, and direct multi-channel output. Nup Imposer prepares correctly
  color-managed source files; the RIP handles output.
