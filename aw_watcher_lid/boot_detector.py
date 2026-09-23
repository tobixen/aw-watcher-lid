"""Boot gap detection for tracking system downtime."""

import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import TYPE_CHECKING

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

        The boot gap is validated against actual ActivityWatch activity:
        window/AFK activity during the supposed gap means the system was
        running without this watcher, so the gap starts where the last such
        activity ended.
        """
        if not self.watcher.config.get("enable_boot_detection", True):
            logger.debug("Boot gap detection disabled")
            return

        # Get current boot time from /proc/uptime
        boot_time = self._get_boot_time()
        if not boot_time:
            logger.warning("Could not determine boot time")
            return

        logger.info(f"System boot time: {boot_time}")

        # Get last event from our lid bucket
        last_event_time = self._get_last_event_time()
        if not last_event_time:
            logger.info("No previous events found, skipping boot gap detection")
            return

        logger.info(f"Last lid event time: {last_event_time}")

        # The system was up (without this watcher) until the last recorded
        # window/AFK activity, so the downtime starts no earlier than that
        gap_start = last_event_time
        last_activity_end = self._get_last_activity_end(last_event_time, boot_time)
        if last_activity_end and last_activity_end > gap_start:
            logger.info(f"Found activity until {last_activity_end}, boot gap starts there")
            gap_start = last_activity_end

        gap_duration = (boot_time - gap_start).total_seconds()
        if gap_duration <= self.boot_gap_threshold:
            logger.debug(f"Boot gap too short: {gap_duration:.0f}s")
            return

        logger.info(
            f"Boot gap detected: {gap_duration:.0f}s ({gap_duration / 3600:.1f}h) "
            f"between {gap_start} and {boot_time}"
        )

        # Create synthetic boot gap event
        self.watcher._send_event(
            timestamp=gap_start,
            duration=gap_duration,
            lid_state=None,
            suspend_state=None,
            boot_gap=True,
            event_source="boot",
        )

    def _get_boot_time(self) -> datetime | None:
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

    def _get_last_event_time(self) -> datetime | None:
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
            event_start_raw = last_event["timestamp"]
            event_duration_raw = last_event["duration"]

            # Handle both datetime and string timestamps
            if isinstance(event_start_raw, str):
                event_start: datetime = datetime.fromisoformat(
                    event_start_raw.replace("Z", "+00:00")
                )
            else:
                event_start = event_start_raw

            # Handle both timedelta and float durations
            if isinstance(event_duration_raw, (int, float)):
                event_duration: timedelta = timedelta(seconds=event_duration_raw)
            else:
                event_duration = event_duration_raw

            event_end: datetime = event_start + event_duration
            return event_end

        except Exception as e:
            logger.error(f"Failed to get last event: {e}")
            return None

    def _get_last_activity_end(self, start_time: datetime, end_time: datetime) -> datetime | None:
        """Find when the last window/AFK activity in a time period ended.

        Args:
            start_time: Start of the period to check
            end_time: End of the period to check

        Returns:
            End time of the latest activity found, or None if no activity
        """
        if self.watcher.testing:
            return None

        last_activity_end: datetime | None = None

        try:
            buckets = self.watcher.client.get_buckets()
        except Exception as e:
            logger.error(f"Failed to get buckets: {e}")
            return None

        for bucket_id in buckets:
            if "window" not in bucket_id and "afk" not in bucket_id:
                continue

            try:
                # aw-server returns events newest first
                events = self.watcher.client.get_events(
                    bucket_id,
                    start=start_time,
                    end=end_time,
                    limit=1,
                )
            except Exception as e:
                logger.debug(f"Failed to query {bucket_id}: {e}")
                continue

            if not events:
                continue
            event_end = min(events[0].timestamp + events[0].duration, end_time)
            logger.debug(f"Found activity in {bucket_id} until {event_end}")
            if last_activity_end is None or event_end > last_activity_end:
                last_activity_end = event_end

        return last_activity_end
