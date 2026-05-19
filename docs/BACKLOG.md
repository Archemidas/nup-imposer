# Backlog — Nup Imposer

All feature ideas, follow-ups, and enhancement requests gathered across the
development sessions for v0.1 – v0.4.  Items are grouped by horizon; the phase
labels are approximate and may shift as priorities change.

Last updated: 2026-05-19

---

## 0.5.x — Production niceties (next up)

### Print marks overlay (`core/marks.py`)
Add a new overlay pass invoked between `_composite` and `save`:
- **Crop marks** — fine hairlines at each cell corner indicating the trim line.
- **Registration marks** — bullseye targets outside the live area for press
  alignment.
- **Colour bars** — CMYK and/or RGB density patches along a non-printing edge
  for on-press quality control.
- Marks should be configurable (size, offset from bleed, colour, enable/disable
  per type) and should work for both TIFF and PDF output.
- GUI: new "Print Marks" group; CLI: `--marks`, `--mark-size`, `--bleed`.

### Per-channel ink coverage statistics in the GUI
Extend the existing TAC check to report per-channel average ink coverage
percentages (C / M / Y / K + any extended channels) alongside the overall TAC
summary popup.  Useful for spotting dominant channels and planning GCR/UCR
adjustments before sending to the RIP.

### User-supplied ink set JSON (`~/.nup-imposer/ink_sets/`)
Mirror the printer preset system: allow users to drop JSON files into
`~/.nup-imposer/ink_sets/` (Windows: `%USERPROFILE%\.nup-imposer\ink_sets\`)
to define custom ink sets without modifying the source.  The registry loader
should merge user sets with built-ins, with user entries winning on ID clash.

### Batch / hot-folder mode
Accept a directory of images and produce a directory of imposed sheets:
```
nup-imposer ./photos/ -n 4 -p Letter -o ./output/
```
Optional `--watch` flag for live processing: monitor the input folder and
process new files as they appear (useful for photo-booth and event workflows).

### Proper gamut-warning overlay
Implement the gamut-check overlay already wired in `color_settings.gamut_check`
— paint out-of-gamut pixels with a configurable highlight colour (default
magenta) in the preview widget.  Currently the flag is stored but the visual
output is identical to a standard soft-proof.

### Page numbering / file naming templates
For multi-sheet batch jobs, support `{name}`, `{n}`, `{page}`, `{date}`
tokens in the output filename.  Example: `{name}_{page:02d}_4up.tif`.

---

## 0.6.x — Polish and usability

### Drag-and-drop input
Accept drag-and-drop of image files onto the GUI window (the preview canvas or
the file-path bar) instead of requiring the Browse dialog.

### Recently-used files
Maintain a "Recent files" list (max 10) in the File menu and restore the last
used file path on startup.

### Layout presets
Let users save and recall a named combination of paper size, n-up count,
margin, and gutter — e.g. "4-up 5×7 glossy standard".  Stored in
`~/.nup-imposer/layout_presets.json`.

### Light / dark theme
Expose a theme toggle (System / Light / Dark) in the user menu.  Qt 6.5+
supports a native `QPalette` dark mode; a custom QSS stylesheet is a fallback
for older builds.

### Restore last session settings
On startup, restore the last-used paper, n-up, DPI, format, ink set, and color
settings from a small config file (`~/.nup-imposer/session.json`).

---

## 1.0 — Stability cut

- Settled public API (`nup_imposer.core.*`) with no breaking changes without a
  major version bump.
- Frozen UI vocabulary: all control labels, menu items, and dialog text locked
  for translation.
- Comprehensive test coverage (target ≥ 90 % line coverage across `core/`).
- Signed Windows installer (`.msi`) via WiX or NSIS; code-signed `.exe` to
  eliminate SmartScreen warnings.
- macOS `.app` bundle (secondary build target).
- Localisation infrastructure (`gettext` / Qt Linguist).

---

## Community / nice-to-have (no milestone assigned)

- **PDF multi-page input** — currently only the first page of a PDF is
  rendered; add a page-picker so users can select which page to impose.
- **Variable-data impostion** — accept a folder of N different images and fill
  each cell with a distinct image (gang-run printing).
- **Bleed extension** — automatically extend edge pixels outward to fill a
  configurable bleed margin beyond the crop marks.
- **In-app profile downloader** — link to manufacturer ICC profile pages for
  each supported printer from within the Quick Preset panel.
- **Export progress bar** — show progress during composite + export for large
  (A0 @ 600 DPI) canvases.
- **Keyboard shortcuts** — Ctrl+R to recalculate, Ctrl+E to export, arrow keys
  to nudge margin/gutter spinners.
- **Undo / redo** for settings changes in the GUI.

---

## Not on the roadmap

These are intentionally out of scope:

- **Profile creation** — spectrophotometer-based profiling (X-Rite i1Pro,
  ColorMunki, etc.) requires hardware-specific software and is beyond the scope
  of an imposition tool.
- **Replacing a RIP** — halftoning, screening, dot-gain curves, and direct ink
  channel driving remain the domain of Wasatch, ColorBurst, Mirage, ErgoSoft,
  and similar tools.
- **Vector imposition** — PDF objects, fonts, and native vector art are
  rasterised today; native vector layout would require a PDF compositor.
- **Spot-colour / Pantone mapping** — custom spot inks need ICC DeviceLink
  profiles and a spectral engine beyond what lcms2 exposes via Pillow.

---

If you have a feature request, open an issue at
[github.com/Archemidas/nup-imposer/issues](https://github.com/Archemidas/nup-imposer/issues).
