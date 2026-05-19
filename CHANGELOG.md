# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [0.4.0] - 2026-05-19

### Added
- Ink channel registry (`core/ink_channels.py`) with 9 built-in ink sets:
  - `cmyk_standard` — Generic 4-color CMYK (TAC 300%)
  - `generic_laser` — Generic color laser CMYK (TAC 200%)
  - `epson_artisan_1400_6color` — Epson Artisan 1400/1430 Claria 6-ch
    (C M Y K + LC LM, TAC 260%)
  - `canon_pro100_8color` — Canon Pixma Pro-100 ChromaLife100+ 8-ch
    (C M Y BK + PBK PC PM GY, TAC 280%)
  - `canon_pro9500ii_10color` — Canon Pixma Pro9500 Mark II Lucia 10-ch
    (C M Y PBK R G GY PGY PC PM, TAC 260%)
  - `epson_p800_8color` — Epson SureColor P800 UltraChrome HD 8-ch
    (C VM Y PBK MBK + LC VLM LK, TAC 240%)
  - `epson_p900_10color` — Epson SureColor P900 UltraChrome PRO10 10-ch
    (adds LLK and V, TAC 250%)
  - `commercial_cmyk_swop` — Commercial offset SWOP v2 (TAC 300%)
  - `sublimation_cmyk` — Sublimation inkjet 4-ch (TAC 220%)
- TAC (Total Area Coverage) estimation (`core/tac.py`):
  - `estimate_tac(image, tac_limit)` — histogram-based O(N) estimator
    (downsamples to ≤1 M pixels, 1021-bucket histogram over raw 0–1020
    channel sums) returning `TACResult` with average / 95th-pct / max /
    pixels_over / fraction_over / exceeds_limit and a formatted `summary()`.
  - `_split_channel_bytes(raw, split_at)` — non-overlapping threshold model
    for deriving light ink channels; guarantees no pixel contributes to both
    main and light simultaneously.
  - `channel_split(cmyk_image, ink_set)` — converts CMYK → N 'L'-mode
    channel images in ink-set order, handling multiple light children from
    the same parent (e.g. LK + LLK from K).
- DeviceN TIFF export (`export_multichannel_tiff` in `core/exporters.py`):
  - Strategy 1: `tifffile` + numpy (LZW, proper InkNames extratags) when
    `tifffile` is installed (`pip install nup-imposer[rip]`).
  - Strategy 2: Built-in pure-Python DEFLATE planar TIFF writer using only
    `struct` + `zlib` — no external deps required. Writes a conformant TIFF
    with PhotometricInterpretation=5 (Separated), InkSet=2, PlanarConfig=2,
    and tags 256/257/258/259/262/273/277/278/279/282/283/284/296/332/333/334
    plus optional 34675 (ICC profile).
  - Strategy 3: Per-channel grayscale TIFF fallback (N individual files) for
    RIPs that accept named grayscale separations directly.
- GUI: new "Ink Set / TAC" group (between Color Management and Output):
  - Ink set combo with n-channel count labels.
  - TAC limit label showing the ink set's paper limit and channel count.
  - "Check TAC…" button — estimates TAC for the loaded image and shows a
    `QMessageBox` summary.
  - Inline color-coded TAC result label (green OK / amber warning / red over).
- GUI: "Multi-channel TIFF (DeviceN / RIP)" added to the Format combo.
  When is_single=False (per-channel fallback), an informational dialog lists
  the generated filenames.
- CLI: `--ink-set ID`, `--tac-warn`, `--tac-error` (exit code 6) flags.
- CLI: `--list-ink-sets` — prints ink sets grouped by workflow with channel
  count and TAC limit.
- CLI: `--format multichannel` — exports DeviceN TIFF using the selected ink
  set (defaults to `cmyk_standard` when `--ink-set` is omitted).
- Windows icon: `assets/icon.ico` — multi-resolution (16→256 px) icon with a
  paper + dashed grid motif, generated with Pillow ImageDraw.
- Docs: `docs/MULTI_INK.md` — full API reference, CLI usage examples, light
  ink derivation technical notes, and a guide to sourcing multi-ink ICC
  profiles.
- Tests: `tests/test_ink_channels.py` (20 tests) and `tests/test_tac.py`
  (24 tests); all 84 tests pass.

### Changed
- Bumped version to 0.4.0.
- `pyproject.toml`: updated description; added `[rip]` optional extras group
  (`tifffile>=2023.1.1`, `numpy>=1.24`).
- `docs/ARCHITECTURE.md`: added `core/ink_channels.py`, `core/tac.py`, and
  `export_multichannel_tiff` documentation; updated "Where future features
  plug in" to mark 0.4.x as shipped.
- `docs/ROADMAP.md`: 0.4.x marked complete with full feature list.

## [0.3.0] - 2026-05-19

### Added
- Printer preset registry (`core/presets.py` + bundled `presets_data.py`)
  with 15 starter presets covering:
  - Epson Artisan 1400/1430 (6-color Claria) - Premium Glossy / Semi-Gloss / Velvet Fine Art
  - Canon Pixma Pro9500 Mark II (10-color Lucia) - PT / Matte / Luster
  - Canon Pixma Pro-100 (8-color ChromaLife100+) - PT
  - Epson SureColor P800/P900 (UltraChrome HD) - Luster / Hot Press Bright
  - Generic Color Laser (sRGB)
  - Commercial CMYK SWOP v2
  - Sublimation: Polyester / Hard substrate / Photo panel / SubliJet generic
- Each preset bundles printer + paper + ink set + ICC filename candidates +
  default rendering intent + BPC default + mirror_output flag + workflow notes.
- Profile resolution: presets search system profile dirs for matching filenames.
  When none match, the preset still applies its intent/BPC/mirror settings
  and the user can Browse manually.
- User-supplied presets via `~/.nup-imposer/presets/*.json` (Windows:
  `%USERPROFILE%\.nup-imposer\presets\`) override builtins by id.
- `ColorSettings.mirror_output` flag - exporters flip the canvas horizontally
  before save when true (sublimation transfer workflow).
- GUI: new "Quick Preset" group above Color Management with workflow filter,
  preset dropdown, and notes panel. Selecting a preset auto-fills intent,
  BPC, mirror, and destination profile (when resolved).
- GUI: new "Mirror output (sublimation)" checkbox in Color Management.
- CLI: `--preset PRESET_ID`, `--list-presets`, `--mirror`, `--no-mirror` flags.
  Explicit `--intent` / `--no-bpc` / `--dest-profile` override the preset.
- Tests: `tests/test_presets.py` - 17 new tests covering registry load,
  resolution, custom presets, preset application.
- Docs: new `docs/PRESETS.md` explains the registry and how to add custom
  presets via JSON.

### Changed
- Bumped version to 0.3.0.
- README features list mentions presets and sublimation mode.
- docs/USAGE.md - new "Quick Preset" walkthrough plus CLI examples.
- docs/ARCHITECTURE.md - presets module entry.
- docs/COLOR_MANAGEMENT.md - 0.3.0 presets section moved to implemented.
- docs/ROADMAP.md - 0.3 marked complete; refocused 0.4+ goals.

## [0.2.0] - 2026-05-19

### Added
- Active ICC color management via `core/color.py` (lcms2 through PIL.ImageCms).
- System profile discovery for Windows (`spool\drivers\color`), macOS
  (`/Library/ColorSync/Profiles` and user/system variants), and Linux
  (`/usr/share/color/icc` and XDG dirs).
- `apply_transform` for source-to-destination ICC conversion with rendering
  intent and black point compensation.
- `soft_proof` rendering pipeline that simulates a destination profile on
  screen, with optional gamut-check overlay support.
- `ColorSettings` dataclass shared between GUI, CLI, and exporters.
- GUI: new "Color Management" group with destination dropdown (incl. system
  profile scan + Browse), rendering intent selector, BPC toggle, soft-proof
  toggle, and gamut-warning checkbox.
- Preview widget re-renders through the soft-proof pipeline when enabled.
- CLI: `--dest-profile`, `--intent`, `--no-bpc` flags.
- Exporters embed the destination profile's bytes when a transform was
  applied (so the file's ICC tag matches its pixel data).
- Test suite: `tests/test_color.py` covers profile loading, transforms,
  soft-proof, `ColorSettings`.

### Changed
- Bumped version to 0.2.0.
- README features list reflects active color management.
- docs/COLOR_MANAGEMENT.md - 0.2.x section moved from "planned" to "shipped".
- docs/ROADMAP.md - 0.2.x marked complete.

## [0.1.0] - 2026-05-19

### Added
- Initial release.
- Core imposition engine with auto rows-x-columns calculation and rotation.
- Multi-format input loader: JPG, PNG, TIFF, PSD, PDF.
- TIFF exporter with embedded ICC profile and accurate DPI tags.
- PDF exporter sized to physical paper dimensions.
- PyQt6 GUI with live preview, paper size presets, custom paper, margin/gutter controls.
- CLI for headless batch use.
- GitHub Actions workflow that builds a Windows .exe and zips releases.
- Local `build_windows.bat` for self-built installs.
- Test suite (paper sizes, layout math).
- Documentation: README, USAGE, ARCHITECTURE, COLOR_MANAGEMENT, ROADMAP.

### Known limitations (carried forward)
- PDF inputs render the first page only.
- No spot color / DeviceN support yet (multi-ink output relies on RIP).
