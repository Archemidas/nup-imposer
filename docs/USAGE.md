# Usage Guide

## GUI walkthrough

### 1. Open an image

`File > Open` or click **Browse...** in the Input Image panel. Supported formats:

| Format | Notes |
|---|---|
| JPG / JPEG | Reads embedded EXIF DPI and ICC profile |
| PNG | Reads DPI from pHYs chunk |
| TIFF | Reads DPI tag and embedded ICC; multi-page TIFFs use the first page |
| PSD | Reads composite layer; preserves color mode (RGB / CMYK) |
| PDF | Rasterizes the first page at 300 DPI by default |

Once loaded, the info panel shows pixel dimensions, DPI, inch dimensions, color mode,
and whether an ICC profile is embedded.

### 2. Pick a paper size

Choose from presets or pick **Custom...** to enter exact inch dimensions.

Common choices:

- **Letter** (8.5 x 11) - office laser/inkjet, photo print labs
- **Super B (13x19)** / **A3+** - Epson Artisan 1430, Canon Pro 9500/9500 II
- **Tabloid (11x17)** - color laser, some inkjets
- **4x6 / 5x7 / 8x10** - photo print sizes

**Orientation**: leave on Auto unless you need to force a specific one. Auto tries
both and picks whichever orientation maximizes filled cell area.

### 3. Set the n-up count and margins

The dropdown includes 1, 2, 3, 4, 6, 8, 9, 10, 12, 16, 20, 25. For other values run
the CLI with `-n N`.

- **Margin**: distance from the edge of paper to the imposition grid. Defaults to 0.25 in.
  Set to your printer's minimum unprintable margin if you want maximum image area.
- **Gutter**: gap between cells. Defaults to 0.125 in. Set 0 for borderless tiling.

Click **Calculate Layout**. The preview shows the paper, the margin guide, the cell
grid, and a thumbnail of your image in each cell. Rotated cells are marked in the
status bar.

### 4. Color management (optional)

**Skip this entire section** if you just want a 4-up sheet to send to the
driver and let Windows handle color. The default settings preserve your
source ICC profile end-to-end.

For active color management:

- **Scan installed profiles** - one click populates the Destination dropdown
  with every ICC profile Windows knows about
  (`C:\Windows\System32\spool\drivers\color\`).
- **Destination** - pick a printer/paper combo (e.g.
  "Pro9500 Glossy Photo Paper"). Or **Browse...** to a custom `.icc/.icm`.
- **Rendering intent**:
  - **Perceptual** - photographs, when you want a pleasing match.
  - **Relative Colorimetric** - proofs and most fine-art workflows.
  - **Saturation** - charts, business graphics.
  - **Absolute Colorimetric** - paper-stock simulation, contract proofs.
- **Black point compensation** - leave on unless your destination profile
  documents otherwise. Matches Adobe's default behavior.
- **Soft-proof preview** - shows in the canvas how the printed result will
  look on screen. Toggle on once you've chosen a destination.
- **Gamut warning** - highlights pixels the destination can't reproduce.

When a destination profile is selected, exports apply the transform and embed
the destination's ICC tag (so the file's pixel data and ICC tag agree).

### 5. Export

- **Resolution**: output DPI. 300 is typical for inkjet; 600 for laser/sharp text.
- **Format**:
  - **TIFF** opens directly in Photoshop, preserves ICC, lossless.
  - **PDF** opens in Acrobat at the correct physical size, easy to send to a RIP.
  - **Both** writes both files in one go.
- **Embed source ICC profile**: leave on unless you have a reason to strip it.

Click **Export...** and pick a base filename. The extension is added per format.

## Color management CLI

Same options as the GUI:

```bash
# Convert to a destination profile with relative colorimetric + BPC
python -m nup_imposer photo.jpg -n 4 -p "Super B (13x19)" \
    --dest-profile "C:\\Windows\\System32\\spool\\drivers\\color\\Pro9500_Glossy.icc" \
    --intent relative

# Saturation intent, no BPC
python -m nup_imposer chart.png -n 9 -p Letter \
    --dest-profile path/to/printer.icc \
    --intent saturation --no-bpc
```

`--intent` accepts `perceptual`, `relative`, `saturation`, or `absolute`.

## CLI examples

```bash
# Help
python -m nup_imposer --help

# 4-up on Letter, embed ICC, save TIFF
python -m nup_imposer photo.jpg -n 4 -p Letter -d 300 -f tiff

# 9-up on Super B, very thin gutters
python -m nup_imposer photo.jpg -n 9 -p "Super B (13x19)" -m 0.125 -g 0.0625

# Custom paper (5x7 sheet) with 2-up
python -m nup_imposer label.jpg -n 2 --paper-custom 5 7 -f both

# Process a PDF input (rasterize first page at 600 DPI)
python -m nup_imposer poster.pdf -n 4 -p Tabloid --pdf-render-dpi 600

# Force landscape paper
python -m nup_imposer wide_image.jpg -n 2 -p Letter --orientation landscape
```

## Output filename convention

If you don't pass `--output`, the CLI writes alongside the input:

```
photo.jpg  ->  photo_4up_letter.tif
```

In the GUI, the same default is offered in the save dialog.

## Tips for print quality

- **Match output DPI to printer capability.** Most consumer inkjets are 1440/2880 dpi
  marketing numbers but accept 300 ppi image data (240 for some workflows).
- **Don't upscale.** If your source is 150 DPI at the final cell size, exporting at
  600 DPI just upsamples - quality won't improve. The cell-size-in-inches divided by
  source-size-in-pixels tells you the effective DPI.
- **TIFF for archival, PDF for sending.** TIFF preserves the most metadata and is
  reopenable in Photoshop with all the layout in place. PDF is the universal "send
  to printer / RIP / shop" container.
- **CMYK input stays CMYK.** Loading a CMYK PSD or TIFF preserves the channels in
  the output. RGB source -> RGB output.
