# Roadmap

## 0.1.x - foundations  [DONE]

- N-up imposition engine
- Multi-format input (JPG, PNG, TIFF, PSD, PDF)
- TIFF + PDF output preserving DPI and embedded ICC
- PyQt6 GUI + CLI
- Windows .exe build pipeline via GitHub Actions

## 0.2.x - active color management  [DONE in 0.2.0]

- `core/color.py` wrapping PIL.ImageCms (lcms2)
- System profile discovery (Windows / macOS / Linux)
- Source-to-destination ICC transforms
- All four rendering intents (Perceptual / Relative / Saturation / Absolute)
- Black point compensation toggle
- Soft-proof preview integrated into the layout canvas
- Gamut-check flag (overlay polish lands in 0.5.x)
- CLI: `--dest-profile`, `--intent`, `--no-bpc`

## 0.3.x - printer presets and sublimation mode  [DONE in 0.3.0]

- Bundled preset registry (15 starter presets) covering Epson Artisan 1400/1430,
  Canon Pro9500 II, Canon Pro-100, Epson SureColor P800/P900, generic laser,
  commercial CMYK, and sublimation workflows
- Profile resolution against system-installed ICCs with graceful fallback
  when filenames don't match
- User-supplied JSON presets via `~/.nup-imposer/presets/` (override builtins)
- Sublimation mode: `mirror_output` flag on `ColorSettings` flips the canvas
  horizontally before save
- GUI Quick Preset group with workflow filter + auto-apply
- CLI: `--preset`, `--list-presets`, `--mirror`, `--no-mirror`

## 0.4.x - multi-ink / RIP-ready output

- 6-color Epson Artisan 1400 channel-level output (CMYK + Cl, Ml)
- 8 to 10-color Canon Pixma Pro9500 Mark II channel-level output
- Multi-channel TIFF export (DeviceN)
- Ink coverage (TAC) estimation with paper-limit warnings
- Spot-channel / named color support

## 0.5.x - production niceties

- Crop / registration marks
- Color bars
- Page numbering / file naming templates
- Batch / hot-folder mode (drop a folder of images, get a folder of imposed sheets)
- Proper gamut-warning overlay with color picker

## 0.6.x - polish

- Drag-and-drop in GUI
- Recently-used files
- Layout presets (save a paper + n-up + margin combo)
- Light/dark theme

## 1.0 - stability cut

- Settled API
- Frozen UI vocabulary
- Comprehensive test coverage
- Signed Windows installer (.msi)

## Not on the roadmap

- Profile *creation* (needs spectrophotometer + hardware-specific software)
- Replacing a RIP (no halftoning, screening, dot-gain curves, direct ink driving)
- Vector imposition for fonts / native PDF objects (rasterizes today)

If you have a feature request, open an issue at
github.com/Archemidas/nup-imposer/issues.
