"""Boot gap detection for tracking system downtime."""

import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from .lid import LidWatcher

logger = logging.getLogger(__name__)


class BootDetector:
    """Detects boot gaps and creates synthetic events for system downtime."""

    def __init__(self, watcher: "LidWatcher") -> None:
        """Initialize the boot detector.

        Args:
            watcher: The LidWatcher instance to notify of boot gaps
        """
        self.watcher = watcher
        self.boot_gap_threshold = watcher.config.get("boot_gap_threshold", 300.0)

    def check_for_boot_gap(self) -> None:
        """Check if there was a gap since last run (system was off/rebooted).

        This is called on startup to detect if the system was shut down
        between the last event and the current boot.
        """
        if not self.watcher.config.get("enable_boot_detection", True):
            logger.debug("Boot gap detection disabled")
            return

        # Get current boot time
        boot_time = self._get_boot_time()
        if not boot_time:
            logger.warning("Could not determine boot time")
            return

        logger.info(f"System boot time: {boot_time}")

        # Get last event from ActivityWatch
        last_event_time = self._get_last_event_time()
        if not last_event_time:
            logger.info("No previous events found, skipping boot gap detection")
            return

        logger.info(f"Last event time: {last_event_time}")

        # Calculate gap
        gap_duration = (boot_time - last_event_time).total_seconds()

        # If gap is significant, create boot gap event
        if gap_duration > self.boot_gap_threshold:
            logger.info(
                f"Boot gap detected: {gap_duration:.0f}s ({gap_duration/3600:.1f}h) "
                f"between {last_event_time} and {boot_time}"
            )

            # Create synthetic boot gap event
            self.watcher._send_event(
                timestamp=last_event_time,
                duration=gap_duration,
                lid_state=None,
                suspend_state=None,
                boot_gap=True,
                event_source="boot",
            )
        else:
            logger.debug(f"Boot gap too short: {gap_duration:.0f}s")

    def _get_boot_time(self) -> Optional[datetime]:
        """Get the system boot time.

        Returns:
            Boot time as datetime, or None if unavailable
        """
        try:
            # Read from /proc/uptime (uptime in seconds)
            uptime_path = Path("/proc/uptime")
            if uptime_path.exists():
                uptime_seconds = float(uptime_path.read_text().split()[0])
                boot_time = datetime.now(timezone.utc) - timedelta(seconds=uptime_seconds)
                return boot_time
        except Exception as e:
            logger.error(f"Failed to read /proc/uptime: {e}")

        # Fallback: try reading from /proc/stat
        try:
            stat_path = Path("/proc/stat")
            if stat_path.exists():
                for line in stat_path.read_text().splitlines():
                    if line.startswith("btime "):
                        boot_timestamp = int(line.split()[1])
                        return datetime.fromtimestamp(boot_timestamp, tz=timezone.utc)
        except Exception as e:
            logger.error(f"Failed to read /proc/stat: {e}")

        return None

    def _get_last_event_time(self) -> Optional[datetime]:
        """Get the timestamp of the last event from ActivityWatch.

        Returns:
            Last event timestamp, or None if no events exist
        """
        if self.watcher.testing:
            logger.debug("Testing mode, skipping last event lookup")
            return None

        try:
            # Query the last event from our bucket
            events = self.watcher.client.get_events(
                self.watcher.bucket_id,
                limit=1,
            )

            if not events:
                return None

            # Get the event end time (timestamp + duration)
            last_event = events[0]
            event_start = last_event["timestamp"]
            event_duration = last_event["duration"]

            # Handle both datetime and string timestamps
            if isinstance(event_start, str):
                event_start = datetime.fromisoformat(event_start.replace("Z", "+00:00"))

            # Handle both timedelta and float durations
            if isinstance(event_duration, (int, float)):
                event_duration = timedelta(seconds=event_duration)

            event_end = event_start + event_duration
            return event_end

        except Exception as e:
            logger.error(f"Failed to get last event: {e}")
            return None
