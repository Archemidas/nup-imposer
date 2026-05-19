# Nup Imposer

A simple desktop application for print production: take an image at any DPI/size
and lay it out as 2-up, 3-up, 4-up, 9-up, 10-up, etc. on a chosen output paper
size. Output opens cleanly in Adobe Photoshop and Adobe Acrobat.

Designed primarily for **Windows**, with both a GUI (PyQt6) and a CLI.

## Features

- **N-up imposition** for 2, 3, 4, 6, 8, 9, 10, 12, 16, 20, 25 copies (or any custom n).
- **Auto-fit** picks the optimal rows-x-columns grid and rotates the source if needed.
- **Multi-format input**: JPG, PNG, TIFF, PSD, PDF.
- **TIFF and PDF output** with embedded source ICC profile and accurate DPI metadata.
- **Paper presets**: Letter, Legal, Tabloid (11x17), Super B (13x19), A3, A3+, A4, A5, 4x6, 5x7, 8x10, mug-wrap, custom.
- **Margin + gutter controls** with a live preview.
- **GUI + CLI** in one app: launch GUI for ad-hoc work, scripted CLI for batch.

## Install

### Option 1: Use the prebuilt Windows release

1. Go to the [Releases page](https://github.com/Archemidas/nup-imposer/releases).
2. Download `NupImposer-vX.Y.Z-Windows.zip`.
3. Unzip anywhere. Run `NupImposer.exe`.

### Option 2: Run from source (any OS)

```bash
git clone https://github.com/Archemidas/nup-imposer
cd nup-imposer
python -m venv .venv
.\.venv\Scripts\activate          # Windows
# source .venv/bin/activate       # macOS/Linux
pip install -r requirements.txt
python -m nup_imposer
```

### Option 3: Build your own Windows .exe

```cmd
build_windows.bat
```

Produces `dist\NupImposer\NupImposer.exe` and `dist\NupImposer-Windows.zip`.

Or push a tag (e.g. `v0.1.0`) and GitHub Actions builds and attaches the zip to a release automatically.

## Quick start (GUI)

1. Launch `NupImposer.exe` (or `python -m nup_imposer`).
2. **Open** an image. Source DPI, pixel size, and inch size are detected.
3. Pick a **paper size** preset, or enter custom dimensions.
4. Choose the **n-up** count and adjust margin/gutter.
5. Hit **Calculate Layout** to preview.
6. Set **output DPI** and **format** (TIFF / PDF / Both).
7. **Export**. Files open natively in Photoshop and Acrobat.

## Quick start (CLI)

```bash
# 4-up on Letter, 300 DPI, TIFF
python -m nup_imposer photo.jpg -n 4 -p Letter -d 300 -f tiff

# 9-up on Super B (13x19), thin margins
python -m nup_imposer photo.jpg -n 9 -p "Super B (13x19)" --margin 0.125 --gutter 0.0625

# Custom paper, both formats
python -m nup_imposer label.pdf -n 12 --paper-custom 13 19 -f both
```

See `python -m nup_imposer --help` for all options.

## Project structure

```
nup-imposer/
+- src/nup_imposer/
|  +- core/           Imposition engine, loaders, exporters
|  +- gui/            PyQt6 main window + preview
|  +- cli.py          argparse entry point
+- tests/             pytest suite
+- docs/              USAGE, ARCHITECTURE, COLOR_MANAGEMENT, ROADMAP
+- .github/workflows/ Windows .exe build pipeline
+- nup_imposer.spec   PyInstaller spec
+- build_windows.bat  Local build script
```

## Roadmap

The full roadmap is in [docs/ROADMAP.md](docs/ROADMAP.md). The highlights:

- **0.2.x** - Active ICC color management: source-to-destination transforms,
  paper/ink profile selection, soft-proofing preview.
- **0.3.x** - Output-target profiles for laser, inkjet, and sublimation workflows.
- **0.4.x** - Multi-ink awareness: 6-color (e.g. Epson Artisan 1400) and 8/10-color
  (e.g. Canon Pixma Pro9500 Mark II) profile selection and RIP-ready prep.
- **0.5.x** - Crop / registration marks, page numbering, batch hot-folder mode.

## License

MIT. See [LICENSE](LICENSE).
