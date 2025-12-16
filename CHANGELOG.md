# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- **BREAKING:** Config file location changed to follow ActivityWatch conventions
  - Old: `~/.config/aw-watcher-lid/config.toml`
  - New: `~/.config/activitywatch/aw-watcher-lid/aw-watcher-lid.toml`
  - Now uses `aw_core.config.load_config_toml` for consistency with other AW components
  - Simplifies code and ensures all ActivityWatch configs are in one place

## [0.1.2] - 2025-12-15

### Added

- Dynamic versioning from git tags using poetry-dynamic-versioning
- Version number now automatically derived from git tags

### Changed

- Build backend updated to use poetry-dynamic-versioning

## [0.1.1] - 2025-12-15

### Added

- Automated publishing to PyPI through GitHub Actions

## [0.1.0] - 2025-12-15

### Added
- Initial implementation of aw-watcher-lid
- Lid event tracking (open/close)
- Suspend/resume event detection
- Boot gap detection for system downtime
- D-Bus integration via systemd-logind
- Journal polling fallback (not recommended)
- Unified event format with status, lid_state, suspend_state fields
- ActivityWatch bucket integration (systemafkstatus event type)
- Systemd service file for auto-start
- Makefile for installation and development tasks
- Comprehensive test suite with pytest
- Type checking with mypy
- Code formatting and linting with ruff
- GitHub Actions CI/CD workflows

[unreleased]: https://github.com/tobixen/aw-watcher-lid/compare/v0.1.2...HEAD
[0.1.2]: https://github.com/tobixen/aw-watcher-lid/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/tobixen/aw-watcher-lid/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/tobixen/aw-watcher-lid/releases/tag/v0.1.0
