"""Tests for LidWatcher."""

import threading
from collections.abc import Iterator
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
from aw_core.models import Event

from aw_watcher_lid.lid import LidWatcher

if TYPE_CHECKING:
    from aw_watcher_lid.dbus_listener import DbusListener


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


class FlakyServerClient:
    """An ActivityWatchClient whose server is down until ``up`` is set."""

    def __init__(self, *args: object, **kwargs: object) -> None:
        self.up = False
        self.buckets: set[str] = set()
        self.heartbeats: list[tuple[str, object]] = []
        self.stored: dict[str, list[Event]] = {}

    def _check(self) -> None:
        if not self.up:
            raise ConnectionError("Connection refused")

    def create_bucket(self, bucket_id: str, event_type: str, queued: bool = False) -> None:
        self._check()
        self.buckets.add(bucket_id)

    def heartbeat(self, bucket_id: str, event: object, pulsetime: float, **kwargs: object) -> None:
        self._check()
        if bucket_id not in self.buckets:
            raise RuntimeError(f"404: no bucket {bucket_id}")
        self.heartbeats.append((bucket_id, event))

    def get_buckets(self) -> dict[str, dict]:
        self._check()
        return {bucket_id: {} for bucket_id in self.buckets}

    def get_events(self, bucket_id: str, limit: int = -1, **kwargs: object) -> list[Event]:
        self._check()
        events = sorted(self.stored.get(bucket_id, []), key=lambda e: e.timestamp, reverse=True)
        return events if limit < 0 else events[:limit]


def _watcher_with_flaky_server() -> tuple[LidWatcher, FlakyServerClient]:
    with patch("aw_watcher_lid.lid.ActivityWatchClient", FlakyServerClient):
        watcher = LidWatcher(testing=False)
    client = watcher.client
    assert isinstance(client, FlakyServerClient)
    return watcher, client


def test_event_while_server_down_is_logged_not_raised(caplog: pytest.LogCaptureFixture) -> None:
    """A failed heartbeat must not escape into the D-Bus/GLib callbacks."""
    watcher, client = _watcher_with_flaky_server()
    watcher._setup_bucket()
    watcher.handle_lid_event("closed")  # must not raise
    assert client.heartbeats == []
    assert "Event dropped" in caplog.text


def test_heartbeat_failure_is_logged_not_raised(caplog: pytest.LogCaptureFixture) -> None:
    """A server going away after the bucket was created must not raise either."""
    watcher, client = _watcher_with_flaky_server()
    client.up = True
    watcher._setup_bucket()
    client.up = False
    watcher.handle_lid_event("open")
    watcher.handle_lid_event("closed")  # closes the "open" event: must not raise
    assert client.heartbeats == []
    assert "Failed to send event" in caplog.text


def test_bucket_recreated_after_deletion_at_runtime() -> None:
    """A bucket deleted while the watcher runs is created again on the next event."""
    watcher, client = _watcher_with_flaky_server()
    client.up = True
    watcher._setup_bucket()
    client.buckets.clear()  # aw-server's database was wiped
    watcher.handle_lid_event("closed")  # fails, and marks the bucket as missing
    watcher.handle_lid_event("open")  # sends the closed lid period
    assert client.buckets == {watcher.bucket_id}
    assert len(client.heartbeats) == 1


def test_bucket_created_lazily_once_server_is_up() -> None:
    """A server that was down at start-up gets the bucket with the first event."""
    watcher, client = _watcher_with_flaky_server()
    watcher._setup_bucket()
    assert client.buckets == set()

    client.up = True
    watcher.handle_lid_event("closed")
    assert client.buckets == {watcher.bucket_id}
    assert len(client.heartbeats) == 1


def test_bucket_not_recreated_for_every_event() -> None:
    """Once the bucket exists, events go straight to heartbeat."""
    watcher, client = _watcher_with_flaky_server()
    client.up = True
    watcher._setup_bucket()
    with patch.object(client, "create_bucket", wraps=client.create_bucket) as create:
        watcher.handle_lid_event("closed")
        watcher.handle_lid_event("open")
    create.assert_not_called()
    assert len(client.heartbeats) == 2


BOOT = datetime(2026, 9, 21, 8, 0, tzinfo=timezone.utc)


def _watcher_with_old_lid_event() -> tuple[LidWatcher, FlakyServerClient]:
    """A flaky server whose lid bucket holds an event that ended 10 h before boot."""
    watcher, client = _watcher_with_flaky_server()
    client.buckets.add(watcher.bucket_id)
    client.stored[watcher.bucket_id] = [
        Event(timestamp=BOOT - timedelta(hours=11), duration=timedelta(hours=1))
    ]
    return watcher, client


@pytest.fixture
def fixed_boot_time() -> Iterator[None]:
    with patch("aw_watcher_lid.boot_detector.BootDetector._get_boot_time", return_value=BOOT):
        yield


def _boot_gaps(client: FlakyServerClient) -> list[object]:
    return [e for _, e in client.heartbeats if e["data"]["boot_gap"]]  # type: ignore[index]


@pytest.mark.usefixtures("fixed_boot_time")
def test_boot_gap_recorded_once_server_is_up() -> None:
    """A server down at start-up gets the boot gap before the first event."""
    watcher, client = _watcher_with_old_lid_event()
    watcher._setup_bucket()
    watcher._check_boot_gap()
    assert client.heartbeats == []

    client.up = True
    watcher.handle_lid_event("closed")
    assert len(client.heartbeats) == 2
    gap = client.heartbeats[0][1]
    assert gap["data"]["boot_gap"] is True  # type: ignore[index]
    assert gap.timestamp == BOOT - timedelta(hours=10)  # type: ignore[attr-defined]
    assert client.heartbeats[1][1]["data"]["lid_state"] == "closed"  # type: ignore[index]

    watcher.handle_lid_event("open")
    assert len(_boot_gaps(client)) == 1


@pytest.mark.usefixtures("fixed_boot_time")
def test_boot_gap_retried_while_server_stays_down() -> None:
    """Events dropped while the server is down do not use up the retry."""
    watcher, client = _watcher_with_old_lid_event()
    watcher._check_boot_gap()
    watcher.handle_lid_event("closed")
    watcher.handle_lid_event("open")
    assert client.heartbeats == []

    client.up = True
    watcher.handle_lid_event("closed")
    assert len(_boot_gaps(client)) == 1


@pytest.mark.usefixtures("fixed_boot_time")
def test_boot_gap_not_repeated_when_server_was_up() -> None:
    watcher, client = _watcher_with_old_lid_event()
    client.up = True
    watcher._setup_bucket()
    watcher._check_boot_gap()
    watcher.handle_lid_event("closed")
    watcher.handle_lid_event("open")
    assert len(_boot_gaps(client)) == 1


class FakeLogindProps:
    """Stands in for logind's Properties interface: answers LidClosed."""

    def __init__(self) -> None:
        self.lid_closed = False

    def Get(self, interface: str, prop: str) -> bool:  # noqa: N802 - D-Bus API name
        assert prop == "LidClosed"
        return self.lid_closed


def _listener_with_fake_logind() -> tuple[LidWatcher, "DbusListener", FakeLogindProps, list[str]]:
    pytest.importorskip("gi")
    dbus = pytest.importorskip("dbus")
    from types import SimpleNamespace

    from aw_watcher_lid.dbus_listener import DbusListener

    watcher = LidWatcher(testing=True)
    listener = DbusListener(watcher)
    props = FakeLogindProps()
    listener.bus = SimpleNamespace(get_object=lambda *args: None)
    listener.dbus = SimpleNamespace(
        Interface=lambda obj, dbus_interface: props, exceptions=dbus.exceptions
    )
    lid_events: list[str] = []
    original = watcher.handle_lid_event

    def record(lid_state: str) -> None:
        lid_events.append(lid_state)
        original(lid_state)

    watcher.handle_lid_event = record  # type: ignore[method-assign]
    return watcher, listener, props, lid_events


def test_periodic_lid_check_does_not_end_suspend() -> None:
    """A lid check right after PrepareForSleep must leave the suspend running."""
    watcher, listener, props, lid_events = _listener_with_fake_logind()
    listener._check_lid_state()
    assert lid_events == ["open"]

    listener._on_prepare_for_sleep(True)
    listener._check_lid_state()  # the 5 s timer, lid still open

    assert lid_events == ["open"]
    assert watcher.current_suspend_state == "suspended"


def test_no_extra_lid_event_after_resume_with_unchanged_lid() -> None:
    watcher, listener, props, lid_events = _listener_with_fake_logind()
    listener._check_lid_state()
    listener._on_prepare_for_sleep(True)
    listener._on_prepare_for_sleep(False)
    listener._check_lid_state()

    assert lid_events == ["open"]
    assert watcher.current_suspend_state == "resumed"


def test_lid_change_across_suspend_is_reported() -> None:
    """Lid closed, suspend, lid opened while asleep: resume reports the open."""
    watcher, listener, props, lid_events = _listener_with_fake_logind()
    props.lid_closed = True
    listener._check_lid_state()
    listener._on_prepare_for_sleep(True)
    props.lid_closed = False
    listener._on_prepare_for_sleep(False)

    assert lid_events == ["closed", "open"]
    assert watcher.current_lid_state == "open"


def test_resume_with_lid_still_closed_is_reported() -> None:
    """Docked or woken by a timer: the closed lid keeps the time system-afk."""
    watcher, listener, props, lid_events = _listener_with_fake_logind()
    props.lid_closed = True
    listener._check_lid_state()
    listener._on_prepare_for_sleep(True)
    listener._on_prepare_for_sleep(False)

    assert lid_events == ["closed", "closed"]
    assert watcher.current_lid_state == "closed"


def test_lid_poll_during_lid_triggered_suspend_leaves_it_running() -> None:
    """Closing the lid suspends; a poll before the freeze must not end the suspend."""
    watcher, listener, props, lid_events = _listener_with_fake_logind()
    listener._check_lid_state()
    props.lid_closed = True
    listener._on_prepare_for_sleep(True)
    listener._check_lid_state()  # the 5 s timer, now seeing the closed lid

    assert lid_events == ["open"]
    assert watcher.current_suspend_state == "suspended"

    listener._on_prepare_for_sleep(False)
    assert lid_events == ["open", "closed"]
