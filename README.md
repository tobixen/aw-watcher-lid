# aw-watcher-lid

ActivityWatch watcher for laptop lid events and system suspend/resume tracking.

## Overview

`aw-watcher-lid` monitors your laptop's lid state and system suspend/resume events, reporting them to ActivityWatch as AFK (away from keyboard) events. This provides more accurate tracking when you close your laptop lid or the system suspends.

## Features

- **Lid event tracking**: Detects when laptop lid is opened/closed
- **Suspend/resume detection**: Tracks system suspend and resume events
- **Boot gap detection**: Identifies system downtime between boots
- **Short cycle filtering**: Ignores lid events shorter than 10 seconds (configurable)
- **D-Bus integration**: Real-time event monitoring via systemd-logind
- **Journal fallback**: Polls journalctl when D-Bus unavailable

## Event Format

Events are posted to ActivityWatch with type `systemafkstatus`:

```json
{
  "timestamp": "2025-01-15T14:30:00Z",
  "duration": 300.0,
  "data": {
    "status": "system-afk",
    "lid_state": "closed",
    "suspend_state": null,
    "boot_gap": false,
    "event_source": "lid"
  }
}
```

## Installation

### Quick Install (recommended)

```bash
# Install the package
make install

# Install and enable systemd service
make install-service
make enable-service
```

### Manual Install

```bash
poetry install --extras dbus
```

## Usage

```bash
# Run directly (if installed)
aw-watcher-lid

# Or via poetry
poetry run aw-watcher-lid

# Or via Make
make test  # Run tests
```

## Configuration

Configuration file: `~/.config/aw-watcher-lid/config.toml`

```toml
# Minimum lid event duration (seconds)
min_lid_duration = 10.0

# Enable boot gap detection
enable_boot_detection = true

# Boot gap threshold (seconds)
boot_gap_threshold = 300.0
```

## Systemd Service

Install the systemd service for automatic startup:

```bash
# Using Makefile (recommended)
make install-service
make enable-service

# Or manually
cp misc/aw-watcher-lid.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable aw-watcher-lid
systemctl --user start aw-watcher-lid
```

Check service status:
```bash
systemctl --user status aw-watcher-lid
```

## Integration with aw-export-timewarrior

This watcher is designed to work with [aw-export-timewarrior](https://github.com/ActivityWatch/aw-export-timewarrior), which merges lid events with regular AFK events to provide accurate time tracking.

## Development

The project includes a Makefile with common development tasks:

```bash
make help            # Show all available commands
make install-dev     # Install with dev dependencies
make test            # Run tests
make lint            # Run linting
make format          # Format code
make clean           # Remove build artifacts
```

## License

MPL-2.0 (following ActivityWatch)
