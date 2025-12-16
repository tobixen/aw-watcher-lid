"""Main LidWatcher class for tracking lid and suspend events."""

import logging
import platform
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional, Union

from aw_client import ActivityWatchClient
from aw_core.models import Event

from .config import load_config

if TYPE_CHECKING:
    from .dbus_listener import DbusListener
    from .journal_listener import JournalListener

logger = logging.getLogger(__name__)


class LidWatcher:
    """Watches for lid and suspend events and reports to ActivityWatch."""

    def __init__(self, testing: bool = False) -> None:
        """Initialize the LidWatcher.

        Args:
            testing: If True, don't connect to ActivityWatch (for testing)
        """
        self.config = load_config()
        self.testing = testing

        # Initialize ActivityWatch client
        if not testing:
            self.client = ActivityWatchClient("aw-watcher-lid", testing=testing)
            self.bucket_id = f"aw-watcher-lid_{platform.node()}"
        else:
            self.client = None  # type: ignore
            self.bucket_id = "aw-watcher-lid_test"

        # Track current state
        self.current_event_start: Optional[datetime] = None
        self.current_lid_state: Optional[str] = None
        self.current_suspend_state: Optional[str] = None

        # Event listener (will be set by start())
        self.listener: Optional[Union["DbusListener", "JournalListener"]] = None

    def _setup_bucket(self) -> None:
        """Create the ActivityWatch bucket if it doesn't exist."""
        try:
            self.client.create_bucket(
                self.bucket_id,
                event_type="systemafkstatus",
                queued=False,  # Create bucket immediately, not queued
            )
            logger.info(f"Bucket created/verified: {self.bucket_id}")
        except Exception as e:
            logger.warning(f"Failed to create bucket (server may be down): {e}")
            logger.info("Will retry bucket creation on first event")

    def handle_lid_event(self, lid_state: str) -> None:
        """Handle a lid state change event.

        Args:
            lid_state: "open" or "closed"
        """
        now = datetime.now(timezone.utc)
        logger.info(f"Lid event: {lid_state} at {now}")

        # If we have a pending event, close it
        if self.current_event_start:
            self._close_current_event(now)

        # Start new event
        self.current_event_start = now
        self.current_lid_state = lid_state
        self.current_suspend_state = None

        # For lid closed, we immediately send the event
        # For lid open, we wait to see the duration
        if lid_state == "closed":
            self._send_event(
                timestamp=now,
                duration=0,
                lid_state=lid_state,
                suspend_state=None,
                boot_gap=False,
                event_source="lid",
            )

    def handle_suspend_event(self, suspend_state: str) -> None:
        """Handle a suspend/resume event.

        Args:
            suspend_state: "suspended" or "resumed"
        """
        now = datetime.now(timezone.utc)
        logger.info(f"Suspend event: {suspend_state} at {now}")

        # If we have a pending event, close it
        if self.current_event_start:
            self._close_current_event(now)

        # Start new event
        self.current_event_start = now
        self.current_suspend_state = suspend_state
        self.current_lid_state = None

        # For suspended, we immediately send the event
        if suspend_state == "suspended":
            self._send_event(
                timestamp=now,
                duration=0,
                lid_state=None,
                suspend_state=suspend_state,
                boot_gap=False,
                event_source="suspend",
            )

    def _close_current_event(self, end_time: datetime) -> None:
        """Close the current event and send it to ActivityWatch.

        Args:
            end_time: When the event ended
        """
        if not self.current_event_start:
            return

        duration = (end_time - self.current_event_start).total_seconds()

        # Send the completed event (no filtering - that happens in aw-export-timewarrior)
        self._send_event(
            timestamp=self.current_event_start,
            duration=duration,
            lid_state=self.current_lid_state,
            suspend_state=self.current_suspend_state,
            boot_gap=False,
            event_source="lid" if self.current_lid_state else "suspend",
        )

        self.current_event_start = None

    def _send_event(
        self,
        timestamp: datetime,
        duration: float,
        lid_state: Optional[str],
        suspend_state: Optional[str],
        boot_gap: bool,
        event_source: str,
    ) -> None:
        """Send an event to ActivityWatch.

        Args:
            timestamp: Event start time
            duration: Event duration in seconds
            lid_state: "open", "closed", or None
            suspend_state: "suspended", "resumed", or None
            boot_gap: Whether this is a boot gap event
            event_source: "lid", "suspend", or "boot"
        """
        # Determine status based on state
        if lid_state == "closed" or suspend_state == "suspended" or boot_gap:
            status = "system-afk"
        else:
            status = "not-afk"

        event_data = {
            "status": status,
            "lid_state": lid_state,
            "suspend_state": suspend_state,
            "boot_gap": boot_gap,
            "event_source": event_source,
        }

        if not self.testing:
            # Create Event object and use heartbeat with large pulsetime for event merging
            event = Event(timestamp=timestamp, duration=duration, data=event_data)
            self.client.heartbeat(
                self.bucket_id,
                event=event,
                pulsetime=3600,  # 1 hour - events within this window will be merged
            )

        logger.info(
            f"Event sent: {event_source} {status} at {timestamp} for {duration}s "
            f"(lid={lid_state}, suspend={suspend_state})"
        )

    def start(self) -> None:
        """Start the watcher.

        This will set up the appropriate event listener (D-Bus or journal)
        and begin monitoring for lid and suspend events.
        """
        # Setup bucket (with retry if server is down)
        if not self.testing:
            self._setup_bucket()

        # Check for boot gaps on startup
        from .boot_detector import BootDetector

        boot_detector = BootDetector(self)
        boot_detector.check_for_boot_gap()

        # Try D-Bus first
        try:
            from .dbus_listener import DbusListener

            self.listener = DbusListener(self)
            logger.info("Using D-Bus listener")
            self.listener.start()
        except (ImportError, Exception) as e:
            logger.warning(f"D-Bus not available: {e}")
            logger.info("Falling back to journal polling")

            # Fall back to journal polling
            from .journal_listener import JournalListener

            self.listener = JournalListener(self)
            self.listener.start()

    def stop(self) -> None:
        """Stop the watcher."""
        # Close any pending event
        if self.current_event_start:
            self._close_current_event(datetime.now(timezone.utc))

        # Stop the listener
        if self.listener:
            self.listener.stop()

        # Disconnect from ActivityWatch (flushes queued requests)
        if not self.testing and self.client:
            self.client.disconnect()

        logger.info("Watcher stopped")
