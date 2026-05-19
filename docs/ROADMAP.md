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

## 0.4.x - multi-ink / RIP-ready output  [DONE in 0.4.0]

- Ink channel registry (`core/ink_channels.py`) — 9 built-in ink sets covering
  CMYK standard, generic laser, Epson Artisan 1400 (6-ch), Canon Pro-100 (8-ch),
  Canon Pro9500 II (10-ch), Epson P800 (8-ch), Epson P900 (10-ch),
  commercial CMYK SWOP, and sublimation CMYK.
- TAC (Total Area Coverage) estimation (`core/tac.py`) — histogram-based O(N)
  estimator returning average / 95th-pct / max / pixels_over with a summary
  formatted for CLI or popup display.
- Light ink channel splitting — non-overlapping threshold model mapping low-density
  pixels to the light ink and high-density pixels to the main ink.
- DeviceN TIFF export (`export_multichannel_tiff`) — three-strategy writer:
  (1) `tifffile` + numpy if installed, (2) built-in pure-Python DEFLATE planar
  TIFF using `struct` + `zlib`, (3) per-channel grayscale TIFF fallback.
- GUI: new "Ink Set / TAC" group with ink set selector, TAC limit display,
  "Check TAC" button, and inline color-coded result label.
- GUI: "Multi-channel TIFF (DeviceN / RIP)" format option in the Output group.
- CLI: `--ink-set`, `--tac-warn`, `--tac-error` flags; `--list-ink-sets`;
  `--format multichannel` for DeviceN export.
- Docs: `docs/MULTI_INK.md` — full API reference, CLI examples, light ink
  derivation notes, where to get multi-ink ICC profiles.

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
