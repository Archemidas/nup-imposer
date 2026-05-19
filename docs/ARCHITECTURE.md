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

### `core/exporters.py`

`_composite(image, layout, dpi)` builds the final canvas in pixels, pastes each
cell with rotation if needed. `export_tiff` saves with LZW compression, DPI tags,
and embedded ICC. `export_pdf` saves a single-page PDF sized to the paper.

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
- **Multi-ink RIP prep (0.4.x)** -> exporters learn to write multi-channel TIFF.
  Loader can read existing channel layouts. Profile registry maps printer +
  paper + ink combos to ICC profiles on disk.
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
