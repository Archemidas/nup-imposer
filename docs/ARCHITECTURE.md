# Architecture

## Layering

```
+---------------------------------------------+
|  gui/  (PyQt6)                              |  user-facing
|  cli.py (argparse)                          |
+----------------------+----------------------+
|         core/        |                      |  domain logic
|  paper_sizes         |                      |
|  imposition (layout) |                      |
|  image_loader        |                      |
|  exporters           |                      |
+----------------------+----------------------+
|         Pillow, PyMuPDF, psd-tools          |  third-party libs
+---------------------------------------------+
```

The GUI and CLI are thin shells over `core/`. Every piece of business logic lives
in `core/` and is testable without Qt.

## Module responsibilities

### `core/paper_sizes.py`

Paper presets as a frozen dataclass `PaperSize(name, width_in, height_in)`. Includes
US, ISO A-series, photo, and sublimation common sizes. `custom_paper_size(w, h)`
builds an ad-hoc size.

### `core/imposition.py`

The core layout calculator. Given:

- a paper size
- an n-up count
- a source aspect ratio
- margins and gutters

it tries every plausible (rows, cols) factor pair against both paper orientations,
scores each by how much of the cell the rotated/non-rotated source fills, and picks
the highest-scoring arrangement. Returns an `ImpositionLayout` with the exact
position and size of every cell.

### `core/image_loader.py`

Format-aware loader. Each input format gets a dedicated path:

- JPG/PNG/TIFF -> `PIL.Image.open` -> read `info["dpi"]` and `info["icc_profile"]`.
- PSD -> `psd_tools.PSDImage.open(...).composite()` -> preserves color mode.
- PDF -> `PyMuPDF (fitz)` page.get_pixmap at the chosen render DPI.

All formats normalize to a `LoadedImage` carrying the PIL image plus original DPI,
pixel size, color mode, ICC bytes (or None), and source path/format.

### `core/ink_channels.py`  [added in 0.4.0]

Ink channel registry for multi-ink / RIP-ready output. Defines:

- `InkChannel` - frozen dataclass (name, abbreviation, index, is_light, parent, split_at).
- `InkSet` - frozen dataclass (id, label, printer, channels tuple, tac_limit, workflow, notes).
- `BUILTIN_INK_SETS` - 9 entries covering 4-colour CMYK, 6-colour Epson Artisan, 8/10-colour
  Canon Pro-100 and Pro9500 II, 8/10-colour Epson P800/P900, commercial CMYK SWOP, sublimation.
- `InkSetRegistry` - find/all/by_workflow/extended_only lookups.
- `get_default_ink_registry()` - convenience for app startup.

### `core/tac.py`  [added in 0.4.0]

TAC (Total Area Coverage) estimation and channel splitting.

- `TACResult` - dataclass (average_pct, p95_pct, max_pct, pixels_over, total_pixels, tac_limit).
- `estimate_tac(image, tac_limit)` - converts to CMYK, builds a 1021-bucket histogram,
  computes average / 95th-pct / max in O(N) without sorting.
- `channel_split(cmyk_image, ink_set)` - returns N `L`-mode PIL images, one per ink channel.
  For light inks, calls `_split_channel_bytes()` which maps values below `split_at` to the
  light channel and above `split_at` to the main channel without overlap.

### `core/presets.py` + `core/presets_data.py`  [added in 0.3.0]

Printer preset registry. `presets_data.py` holds `BUILTIN_PRESETS`, a list of
dicts describing each preset (id, label, printer, paper, ink_set, profile
filename candidates, intent default, BPC default, workflow tag, mirror_output
flag, notes). `presets.py` defines:

- `PrinterPreset` - frozen dataclass for one entry.
- `PresetRegistry` - holds bundled + user presets, exposes `find`, `all`,
  `by_workflow`, `resolve`.
- `load_user_presets()` - reads JSON files from `~/.nup-imposer/presets/`
  (Windows: `%USERPROFILE%\\.nup-imposer\\presets\\`).
- `resolve_profile_path()` - scans system profile dirs for matching filenames.
- `get_default_registry()` - convenience for app startup.

`core.apply_preset_to_settings(preset, settings)` mutates a `ColorSettings`
to match the preset's intent / BPC / mirror / destination profile (when
resolved). Preserves the existing destination if the preset's filename
candidates do not match anything on disk.

### `core/color.py`  [added in 0.2.0]

ICC color management wrapper around `PIL.ImageCms` (lcms2). Exposes:

- `system_profile_dirs()` and `list_installed_profiles()` for discovery.
- `read_profile_info(path)` -> `ProfileInfo(name, color_space, device_class)`.
- `apply_transform(image, src, dst, intent, bpc)` - main source->destination.
- `soft_proof(image, src, proof, display, ...)` - on-screen simulation.
- `RenderingIntent` enum and `ColorSettings` dataclass shared with GUI/CLI.

The module is pure-logic with no Qt dependency; all GUI integration lives in
`gui/main_window.py`.

### `core/exporters.py`

`_composite(image, layout, dpi)` builds the final canvas in pixels, pastes each
cell with rotation if needed. Optionally runs through `_maybe_apply_color_transform`
(0.2.0+) which calls `color.apply_transform` when a destination profile is set,
then `_maybe_mirror` (0.3.0+) which flips horizontally for sublimation.
`export_tiff` saves with LZW compression, DPI tags, and embedded ICC (either
the original embedded profile or the destination profile after a transform).
`export_pdf` saves a single-page PDF sized to the paper.

`export_multichannel_tiff` (0.4.0+) composites → colour-transforms → channel-splits
then tries three strategies: (1) `tifffile` + numpy for LZW DeviceN, (2) built-in
`_build_devicen_tiff()` pure-Python DEFLATE planar TIFF writer using `struct` +
`zlib`, (3) per-channel grayscale TIFF fallback.  `_build_devicen_tiff()` writes a
conformant TIFF IFD with tags 256/257/258/259/262/273/277/278/279/282/283/284/296/
332/333/334 and optional 34675 (ICC profile).

### `gui/`

- `app.py` - QApplication bootstrap.
- `main_window.py` - the form: file picker, paper/orientation, n/margin/gutter,
  output DPI/format, export.
- `preview_widget.py` - custom `QWidget` that paints the layout to scale with
  thumbnails in each cell.

### `cli.py`

argparse front end. Mirrors GUI options 1:1 so headless batch use stays in sync.

## Data flow

```
file -> load_image -> LoadedImage
                          |
                          v
            compute_layout(paper, n, aspect, ...)
                          |
                          v
                   ImpositionLayout
                          |
                          v
              export_tiff / export_pdf
                          |
                          v
                  *.tif / *.pdf
```

## Why these libraries

| Library | Why |
|---|---|
| Pillow | Best-supported Python image library, full TIFF metadata control, broad mode support (RGB, CMYK, L). |
| PyMuPDF (fitz) | Fast, accurate PDF rendering and parsing. MIT-friendly mode available via AGPL/commercial. |
| psd-tools | Pure-Python PSD reader without needing Photoshop installed. |
| PyQt6 | Mature, native-looking GUI on Windows. Free under GPL or commercial license. |
| PyInstaller | Most reliable Python -> Windows .exe path. |

## Where future features plug in

- **ICC transforms (0.2.x)** -> new `core/color.py` module wrapping `PIL.ImageCms`.
  Exporters get a `dest_profile` argument. GUI gets a "Color Management" group.
- **Multi-ink RIP prep (0.4.x - shipped)** -> new `core/ink_channels.py` +
  `core/tac.py`; `export_multichannel_tiff` in exporters; GUI Ink Set / TAC group;
  CLI `--ink-set`, `--tac-warn`, `--tac-error`, `--list-ink-sets`.
- **Crop marks / page numbering (0.5.x)** -> a new `core/marks.py` overlay pass
  invoked between `_composite` and `save`.

## Testing

`pytest` runs the suite in `tests/`. Layout math is the most testable piece - we
can verify cell counts, dimensions, and rotation decisions without touching disk
or running the GUI. The GitHub Actions workflow runs tests before building the
exe.

## Build

PyInstaller, configured by `nup_imposer.spec`. One-folder distribution (faster
startup than one-file). Excludes tkinter, matplotlib, scipy to keep the bundle
smaller. The GitHub Actions workflow builds on `windows-latest` and uploads the
zipped distribution as both an artifact and a Release asset when triggered by a
tag push.
