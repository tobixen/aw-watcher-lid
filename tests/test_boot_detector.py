"""Tests for BootDetector."""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

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
