# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

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
