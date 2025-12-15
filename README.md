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
# One-command setup (install + enable service)
make install-all

# Or step by step:
make install              # Install the package
make enable-service       # Install and start the service
```

### Manual Install

```bash
# Install with D-Bus support (recommended)
poetry install --extras dbus

# Or basic install (will use journal polling fallback)
poetry install
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

The systemd service runs aw-watcher-lid automatically on login.

### Service Management

```bash
# Check status
systemctl --user status aw-watcher-lid

# View logs
journalctl --user -u aw-watcher-lid -f

# Stop/start manually
systemctl --user stop aw-watcher-lid
systemctl --user start aw-watcher-lid

# Disable auto-start
make disable-service

# Uninstall service completely
make uninstall-service
```

**Note**: The service file uses `poetry run` to execute the watcher from the project directory. Make sure the project is located at `~/activitywatch/aw-watcher-lid` or update the `WorkingDirectory` in the service file.

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
