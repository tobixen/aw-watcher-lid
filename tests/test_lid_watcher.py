"""Tests for LidWatcher."""

import threading
from unittest.mock import patch

import pytest

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


def test_stop_idempotent() -> None:
    """Test that calling stop() twice does not raise."""
    watcher = LidWatcher(testing=True)
    watcher.handle_lid_event("closed")
    watcher.stop()
    watcher.stop()  # should not raise


class NeverConnectedClient:
    """Like aw-client's ActivityWatchClient when connect() was never called."""

    def __init__(self, *args: object, **kwargs: object) -> None:
        pass

    def disconnect(self) -> None:
        raise RuntimeError("cannot join thread before it is started")


def test_stop_with_unconnected_client_does_not_raise() -> None:
    """stop() must not fail on a client whose request queue was never started."""
    with patch("aw_watcher_lid.lid.ActivityWatchClient", NeverConnectedClient):
        watcher = LidWatcher(testing=False)
    watcher.stop()


def _start_in_thread(watcher: LidWatcher) -> threading.Thread:
    thread = threading.Thread(target=watcher.start, daemon=True)
    thread.start()
    thread.join(timeout=5)
    return thread


def test_stop_during_startup_makes_start_return() -> None:
    """A SIGTERM while the bucket is set up must not leave start() blocking."""
    watcher = LidWatcher(testing=True)
    with patch(
        "aw_watcher_lid.boot_detector.BootDetector.check_for_boot_gap",
        side_effect=lambda: watcher.stop(),
    ):
        thread = _start_in_thread(watcher)
    assert not thread.is_alive()


# PyGObject warns about its own deprecated GLib aliases on import.
@pytest.mark.filterwarnings("ignore::DeprecationWarning")
def test_dbus_loop_quits_when_stopped_before_it_runs() -> None:
    """stop() before the GLib loop exists must still end DbusListener.start()."""
    pytest.importorskip("gi")
    pytest.importorskip("dbus")
    from aw_watcher_lid.dbus_listener import DbusListener

    watcher = LidWatcher(testing=True)
    listener = DbusListener(watcher)
    watcher.listener = listener
    with patch.object(listener, "_check_lid_state", side_effect=lambda: watcher.stop()):
        thread = threading.Thread(target=listener.start, daemon=True)
        thread.start()
        thread.join(timeout=5)
    assert not thread.is_alive()
