"""Tests for LidWatcher."""

from aw_watcher_lid.lid import LidWatcher


def test_lid_watcher_init() -> None:
    """Test that LidWatcher can be initialized in testing mode."""
    watcher = LidWatcher(testing=True)
    assert watcher is not None
    assert watcher.bucket_id == "aw-watcher-lid_test"
    assert watcher.current_event_start is None


def test_handle_lid_closed() -> None:
    """Test handling lid closed event."""
    watcher = LidWatcher(testing=True)
    watcher.handle_lid_event("closed")

    assert watcher.current_event_start is not None
    assert watcher.current_lid_state == "closed"


def test_handle_lid_open() -> None:
    """Test handling lid open event after close."""
    watcher = LidWatcher(testing=True)

    # Close lid
    watcher.handle_lid_event("closed")
    start_time = watcher.current_event_start

    # Open lid (this should close the previous event)
    watcher.handle_lid_event("open")

    # New event should have started
    assert watcher.current_event_start is not None
    assert watcher.current_event_start != start_time
    assert watcher.current_lid_state == "open"


def test_handle_suspend() -> None:
    """Test handling suspend event."""
    watcher = LidWatcher(testing=True)
    watcher.handle_suspend_event("suspended")

    assert watcher.current_event_start is not None
    assert watcher.current_suspend_state == "suspended"


def test_handle_resume() -> None:
    """Test handling resume event after suspend."""
    watcher = LidWatcher(testing=True)

    # Suspend
    watcher.handle_suspend_event("suspended")
    start_time = watcher.current_event_start

    # Resume (this should close the previous event)
    watcher.handle_suspend_event("resumed")

    # New event should have started
    assert watcher.current_event_start is not None
    assert watcher.current_event_start != start_time
    assert watcher.current_suspend_state == "resumed"
