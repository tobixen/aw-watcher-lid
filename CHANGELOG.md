# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[unreleased]: https://github.com/tobixen/aw-watcher-lid/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/tobixen/aw-watcher-lid/releases/tag/v0.1.0
