# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

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

### Known limitations
- Color management is preserve-only (source ICC carried through). Active CMS
  transforms come in 0.2.x. See docs/ROADMAP.md.
- PDF inputs render the first page only.
- No spot color / DeviceN support yet (multi-ink output relies on RIP).
