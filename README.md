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

```bash
# Install the watcher
make install

# Or manually
poetry install
```

## Usage

### Method 1: aw-qt Integration (Recommended)

The recommended way to run aw-watcher-lid is through the ActivityWatch GUI (aw-qt), which will manage starting and stopping the watcher automatically.

**To configure aw-qt to start the watcher:**

1. Find your aw-qt config file (usually `~/.config/activitywatch/aw-qt/aw-qt.toml`)
2. Add aw-watcher-lid to the watchers list:

```toml
[aw-qt]
autostart_modules = ["aw-server", "aw-watcher-afk", "aw-watcher-window", "aw-watcher-lid"]
```

3. Restart aw-qt

The watcher will now start automatically when you launch ActivityWatch.

### Method 2: Systemd Service

If you prefer to run the watcher independently as a systemd user service:

```bash
# Install and enable the service
make enable-service

# Check status
systemctl --user status aw-watcher-lid

# View logs
journalctl --user -u aw-watcher-lid -f
```

### Method 3: Manual Execution

For testing or development:

```bash
# Run directly
poetry run aw-watcher-lid

# Or after install
aw-watcher-lid
```

## Configuration

Configuration file: `~/.config/aw-watcher-lid/config.toml`

```toml
# Enable boot gap detection
enable_boot_detection = true

# Boot gap threshold (seconds)
# Gaps longer than this are recorded as system downtime
boot_gap_threshold = 300.0

# Polling interval when using journal fallback (seconds)
journal_poll_interval = 60.0
```

**Note:** The watcher reports ALL lid events and suspend/resume actions. Event filtering (e.g., ignoring short cycles) should be configured in aw-export-timewarrior, not in the watcher itself.

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

The watcher reports ALL lid closures and suspend actions. Event filtering (e.g., ignoring cycles shorter than 10 seconds) is handled in aw-export-timewarrior, not in the watcher itself.

## Technical Details

### D-Bus Requirement

**aw-watcher-lid requires D-Bus** to monitor lid and suspend events via systemd-logind. D-Bus is included as a standard dependency and does not require root permissions.

The watcher uses:
- `org.freedesktop.login1.Manager` interface for suspend/resume events
- `org.freedesktop.UPower` device properties for lid state changes

### Journal Fallback (Not Recommended)

A journal polling fallback is included in the code but **is not recommended** and **not properly tested**.

The journal fallback:
- Polls `journalctl` for systemd-logind messages every 60 seconds
- Requires the service to run with root privileges OR user to be in the `systemd-journal` group
- Has higher latency than D-Bus (up to 60s delay)
- May miss rapid lid open/close cycles

**If D-Bus is not available on your system, it's better to fix the D-Bus installation than to use the journal fallback.**

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
