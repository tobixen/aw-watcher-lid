# TODO

## High Priority

- [ ] Fix the 3 failing integration tests in aw-export-timewarrior
  - Complex AFK state transition edge cases
  - Files: `tests/test_lid_afk.py`
  - Tests: `test_lid_priority_over_afk`, `test_boot_gap_handling`, `test_suspend_resume_cycle`

## Medium Priority

- [ ] Add link to aw-watcher-lid in ActivityWatch ecosystem
  - Update ActivityWatch fork documentation
  - Consider submitting PR to main ActivityWatch project

- [ ] Production testing on real hardware
  - Test on different laptop models
  - Verify D-Bus integration across distributions
  - Test boot gap detection with real reboots
  - Test suspend/resume cycles

- [ ] Create v0.1.0 release on GitHub
  - Tag the current commit
  - Write release notes highlighting features
  - Include installation instructions

## Low Priority

- [ ] Consider removing journal polling fallback entirely
  - Currently marked as "not recommended" and "not properly tested"
  - Adds complexity without clear benefit (D-Bus is standard on modern systems)
  - Files: `aw_watcher_lid/journal_listener.py`, `aw_watcher_lid/lid.py`

- [ ] Investigate heartbeat API warning
  - Warning: `ActivityWatchClient.heartbeat() got an unexpected keyword argument 'timestamp'`
  - May be related to aw-client version compatibility
  - Location: `aw_watcher_lid/dbus_listener.py`

- [ ] Add udev/acpi monitoring as alternative to D-Bus polling
  - Could provide more direct lid event detection
  - Would complement existing D-Bus approach
  - Research needed: pros/cons vs current implementation

- [ ] Improve documentation
  - Add troubleshooting section
  - Add FAQ for common issues
  - Add examples of aw-qt configuration for different setups

- [ ] Add CI/CD pipeline
  - Automated testing on push
  - Linting and formatting checks
  - Maybe test on multiple Python versions (if expanding beyond 3.13+)

## Completed ✅

- [x] Make D-Bus a required dependency
- [x] Remove 10s event filtering from watcher (moved to aw-export-timewarrior)
- [x] Document aw-qt integration as recommended method
- [x] Add Makefile for easier installation
- [x] Fix systemd service installation
- [x] Publish repository on GitHub
- [x] Add repository topics/tags on GitHub
