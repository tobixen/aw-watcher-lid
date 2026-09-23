"""Tests for BootDetector."""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from aw_core.models import Event

from aw_watcher_lid.boot_detector import BootDetector
from aw_watcher_lid.lid import LidWatcher


def test_boot_detector_init() -> None:
    """Test that BootDetector can be initialized."""
    watcher = LidWatcher(testing=True)
    detector = BootDetector(watcher)

    assert detector is not None
    assert detector.boot_gap_threshold == 300.0  # Default threshold


def test_get_boot_time() -> None:
    """Test getting system boot time."""
    watcher = LidWatcher(testing=True)
    detector = BootDetector(watcher)

    boot_time = detector._get_boot_time()

    # Should return a datetime
    assert boot_time is not None
    assert isinstance(boot_time, datetime)

    # Boot time should be in the past
    assert boot_time < datetime.now(timezone.utc)


def test_check_for_boot_gap_disabled() -> None:
    """Test that boot gap detection can be disabled."""
    watcher = LidWatcher(testing=True)
    watcher.config["enable_boot_detection"] = False

    detector = BootDetector(watcher)
    detector.check_for_boot_gap()  # Should do nothing


@patch("aw_watcher_lid.boot_detector.BootDetector._get_boot_time")
@patch("aw_watcher_lid.boot_detector.BootDetector._get_last_event_time")
def test_check_for_boot_gap_no_previous_events(
    mock_last_event: MagicMock, mock_boot_time: MagicMock
) -> None:
    """Test boot gap detection when no previous events exist."""
    watcher = LidWatcher(testing=True)
    detector = BootDetector(watcher)

    # Mock boot time
    mock_boot_time.return_value = datetime.now(timezone.utc)

    # No previous events
    mock_last_event.return_value = None

    # Should not raise, just log and return
    detector.check_for_boot_gap()


@patch("aw_watcher_lid.boot_detector.BootDetector._get_boot_time")
@patch("aw_watcher_lid.boot_detector.BootDetector._get_last_event_time")
def test_check_for_boot_gap_short_gap(
    mock_last_event: MagicMock, mock_boot_time: MagicMock
) -> None:
    """Test boot gap detection with a short gap (below threshold)."""
    watcher = LidWatcher(testing=True)
    watcher._send_event = MagicMock()  # Mock event sending

    detector = BootDetector(watcher)

    now = datetime.now(timezone.utc)
    mock_boot_time.return_value = now
    mock_last_event.return_value = now - timedelta(seconds=60)  # 60s gap (< 300s threshold)

    detector.check_for_boot_gap()

    # Should not send event (gap too short)
    watcher._send_event.assert_not_called()


@patch("aw_watcher_lid.boot_detector.BootDetector._get_boot_time")
@patch("aw_watcher_lid.boot_detector.BootDetector._get_last_event_time")
def test_check_for_boot_gap_long_gap(mock_last_event: MagicMock, mock_boot_time: MagicMock) -> None:
    """Test boot gap detection with a long gap (above threshold)."""
    watcher = LidWatcher(testing=True)
    watcher._send_event = MagicMock()  # Mock event sending

    detector = BootDetector(watcher)

    now = datetime.now(timezone.utc)
    last_event = now - timedelta(hours=2)  # 2 hour gap (> 300s threshold)

    mock_boot_time.return_value = now
    mock_last_event.return_value = last_event

    detector.check_for_boot_gap()

    # Should send a boot gap event
    watcher._send_event.assert_called_once()

    # Check the event parameters
    call_args = watcher._send_event.call_args
    assert call_args[1]["boot_gap"] is True
    assert call_args[1]["event_source"] == "boot"
    assert call_args[1]["timestamp"] == last_event
    assert call_args[1]["duration"] > 7000  # ~2 hours in seconds


class FakeAWClient:
    """Mimics aw-server's get_events: range-filtered, newest first, limited."""

    def __init__(self, buckets: dict[str, list[Event]]) -> None:
        self.buckets = buckets

    def get_buckets(self) -> dict[str, dict]:
        return {bucket_id: {} for bucket_id in self.buckets}

    def get_events(
        self,
        bucket_id: str,
        limit: int = -1,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> list[Event]:
        events = [
            e
            for e in self.buckets[bucket_id]
            if (start is None or e.timestamp + e.duration > start)
            and (end is None or e.timestamp < end)
        ]
        events.sort(key=lambda e: e.timestamp, reverse=True)
        return events if limit < 0 else events[:limit]


def _detector_with_activity(
    activity: list[Event], boot_time: datetime, last_lid_event_end: datetime
) -> tuple[BootDetector, MagicMock]:
    watcher = LidWatcher(testing=True)
    watcher.testing = False
    watcher.client = FakeAWClient(  # type: ignore[assignment]
        {"aw-watcher-window_host": activity, "aw-watcher-lid_host": []}
    )
    send = MagicMock()
    watcher._send_event = send  # type: ignore[method-assign]
    detector = BootDetector(watcher)
    detector._get_boot_time = lambda: boot_time  # type: ignore[method-assign]
    detector._get_last_event_time = lambda: last_lid_event_end  # type: ignore[method-assign]
    return detector, send


def test_boot_gap_starts_after_last_activity() -> None:
    """Watcher dead all week: only the downtime after the last activity is a gap."""
    boot = datetime(2026, 9, 21, 8, 0, tzinfo=timezone.utc)  # Monday 08:00
    last_lid = boot - timedelta(days=7) + timedelta(hours=1)  # previous Monday 09:00
    tuesday = Event(timestamp=last_lid + timedelta(days=1), duration=timedelta(hours=8))
    friday_end = datetime(2026, 9, 18, 17, 0, tzinfo=timezone.utc)
    friday = Event(timestamp=friday_end - timedelta(hours=8), duration=timedelta(hours=8))

    detector, send = _detector_with_activity([tuesday, friday], boot, last_lid)
    detector.check_for_boot_gap()

    send.assert_called_once()
    kwargs = send.call_args[1]
    assert kwargs["timestamp"] == friday_end
    assert kwargs["duration"] == (boot - friday_end).total_seconds()


def test_boot_gap_skipped_when_activity_runs_up_to_boot() -> None:
    """Activity ending just before boot means there was no real downtime."""
    boot = datetime(2026, 9, 21, 8, 0, tzinfo=timezone.utc)
    last_lid = boot - timedelta(hours=10)
    work = Event(
        timestamp=last_lid + timedelta(hours=1), duration=timedelta(hours=9) - timedelta(seconds=60)
    )

    detector, send = _detector_with_activity([work], boot, last_lid)
    detector.check_for_boot_gap()

    send.assert_not_called()


def test_boot_gap_without_activity_covers_whole_gap() -> None:
    boot = datetime(2026, 9, 21, 8, 0, tzinfo=timezone.utc)
    last_lid = boot - timedelta(hours=10)

    detector, send = _detector_with_activity([], boot, last_lid)
    detector.check_for_boot_gap()

    send.assert_called_once()
    assert send.call_args[1]["timestamp"] == last_lid
    assert send.call_args[1]["duration"] == (boot - last_lid).total_seconds()
