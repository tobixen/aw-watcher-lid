# TODO

## Medium Priority

- [ ] Production testing on real hardware  **help needed**
  - Test on different laptop models
  - Verify D-Bus integration across distributions
  - Test boot gap detection with real reboots
  - Test suspend/resume cycles

- [ ] Recover when the ActivityWatch server is down at first start
  - `_setup_bucket()` logs "Will retry bucket creation on first event", but nothing retries
  - If the bucket does not exist yet, every heartbeat fails until the watcher is restarted,
    and `_send_event()` lets the exception escape into the D-Bus/GLib callbacks
  - Fix: create the bucket lazily in `_send_event()` (a `_bucket_ready` flag) and log
    heartbeat failures instead of raising
  - File: `aw_watcher_lid/lid.py`

- [ ] Periodic lid check emits spurious events around suspend/resume
  - `_periodic_lid_check()` compares logind's lid state with `current_lid_state`, which
    `handle_suspend_event()` resets to None
  - If the 5 s timer fires between PrepareForSleep(True) and the actual sleep, it closes
    the suspend event and starts a new "closed" lid event; after every resume it emits
    an extra "open" event
  - Fix: track the last lid state reported by logind separately from the event state
  - File: `aw_watcher_lid/dbus_listener.py`

## Low Priority

- [ ] Consider removing journal polling fallback entirely
  - Currently marked as "not recommended" and "not properly tested"
  - Adds complexity without clear benefit (D-Bus is standard on modern systems)
  - Files: `aw_watcher_lid/journal_listener.py`, `aw_watcher_lid/lid.py`

- [ ] Add udev/acpi monitoring as alternative to D-Bus polling
  - Could provide more direct lid event detection
  - Would complement existing D-Bus approach
  - Research needed: pros/cons vs current implementation

- [ ] Improve documentation
  - Add troubleshooting section
  - Add FAQ for common issues
  - Add examples of aw-qt configuration for different setups

## Completed ✅

- [x] Add link to aw-watcher-lid in ActivityWatch ecosystem
  - PR to ActivityWatch docs submitted and accepted
- [x] Make D-Bus a required dependency
- [x] Remove 10s event filtering from watcher (moved to aw-export-timewarrior)
- [x] Document aw-qt integration as recommended method
- [x] Add Makefile for easier installation
- [x] Fix systemd service installation
- [x] Publish repository on GitHub
- [x] Add repository topics/tags on GitHub
- [x] Add CI/CD pipeline (GitHub Actions for tests and linting)
- [x] Address integration test failures (marked 3 edge cases as skipped)
- [x] Fix heartbeat API warning (use Event object instead of individual parameters)
- [x] Fix all CI/CD pipeline errors (ruff, mypy, formatting)
- [x] Create CHANGELOG.md following KeepAChangelog standard
- [x] Prepare v0.1.0 release (ready for signed tag and GitHub release)
- [x] Publish to PyPI with automated GitHub Actions workflow
- [x] Set up PyPI Trusted Publishing for automatic releases on tag push
