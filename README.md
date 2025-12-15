# aw-watcher-lid

ActivityWatch watcher for laptop lid events and system suspend/resume tracking.

## Disclaimer

This project was made using the Claude AI service heavily.  This time no code reviews utilizing "Natural Human Stupidity" has been made.  NHS has been applied to some of the documentation and some testing efforts.

## Overview

`aw-watcher-lid` monitors your laptop's lid state and system suspend/resume events, reporting them to ActivityWatch as AFK (away from keyboard) events.

## Motivation

I'm using `aw-watcher-window-wayland` and it does a fairly good job at tracking my afk status.  I decided to create this watcher while having some bugs with the afk-handling in my aw-export-timewarrior script.  The bugs have been found and dealt with now - but I still think watching the lid status may be useful.  At least for me, this script gives no false postives.  If the lid is closed, I'm by definition away from its keyboard and most likely not doing useful work on it.  (Your situation may of course be different, with external keyboard or other means of working with the laptop).  (False negatives is another thing - the lid may very well be open even if I'm afk - but I may probably train myself to always close the lid before leaving the computer).

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

### From PyPI (Recommended)

```bash
# Install with pip
pip install aw-watcher-lid

# Or with pipx (isolated environment)
pipx install aw-watcher-lid
```

### From Source (Development)

```bash
# Clone the repository
git clone https://github.com/tobixen/aw-watcher-lid.git
cd aw-watcher-lid

# Install with Poetry
poetry install

# Or use the Makefile
make install
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

**For PyPI installations:**

```bash
# Download and install the service file
curl -o ~/.config/systemd/user/aw-watcher-lid.service \
  https://raw.githubusercontent.com/tobixen/aw-watcher-lid/main/misc/aw-watcher-lid.service

# Enable and start the service
systemctl --user daemon-reload
systemctl --user enable --now aw-watcher-lid

# Check status
systemctl --user status aw-watcher-lid

# View logs
journalctl --user -u aw-watcher-lid -f
```

**For source installations:**

```bash
# Install and enable the service using the Makefile
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

**TODO:** The journal polling fallback should probably be removed completely from the codebase. It adds complexity and is not the correct approach for this functionality.

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
