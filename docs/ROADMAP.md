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

## 0.3.x - target presets

- Profile registry: printer + paper + ink combo -> ICC path
- One-click "Print to Epson Artisan 1400 + Premium Glossy"
- Sublimation mode (auto-mirror, sub-paper profile, correct intent)
- User-importable profile bundles

## 0.4.x - multi-ink / RIP-ready output

- 6-color Epson Artisan 1400 support (CMYK + Cl, Ml)
- 8 to 10-color Canon Pixma Pro9500 Mark II support
- Multi-channel TIFF export (DeviceN)
- Ink coverage (TAC) estimation

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
