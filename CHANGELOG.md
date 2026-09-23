# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html) - except, for pre-releases PEP440 takes precedence.

## [Unreleased]

### Added

- `--version` / `-V` command line flag
- The lid state is polled every 5 seconds, so lid changes are recorded even when no D-Bus signal arrives

### Fixed

- Boot gaps no longer cover time when the system was running but aw-watcher-lid was not; the gap now starts where the last window/AFK activity ended

### Changed

- Build system migrated from Poetry to hatchling + hatch-vcs; Poetry is no longer needed to install or develop the package.  `__version__` now comes from the git tag instead of being hardcoded (it was stuck at `0.1.0`)
- `make install` now installs the `aw-watcher-lid` command with uv, pipx or `pip --user` (whichever is available) instead of into a Poetry virtualenv.  `make install-dev` is renamed to `make dev`
- `make install-service` writes the absolute path of the installed script into the systemd unit, as systemd does not search `~/.local/bin`
- Minimum Python version lowered from 3.13 to 3.10; CI tests 3.10 to 3.14
- `aw-core` is now declared as a direct dependency (it was only pulled in via `aw-client`)
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
