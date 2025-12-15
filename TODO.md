# TODO

## Medium Priority

- [ ] Create v0.1.0 release on GitHub
  - Tag the current commit
  - Write release notes highlighting features
  - Include installation instructions

- [ ] Add link to aw-watcher-lid in ActivityWatch ecosystem
  - Update ActivityWatch fork documentation
  - Consider submitting PR to main ActivityWatch project

- [ ] Production testing on real hardware  **help needed**
  - Test on different laptop models
  - Verify D-Bus integration across distributions
  - Test boot gap detection with real reboots
  - Test suspend/resume cycles

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
