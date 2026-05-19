# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

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
