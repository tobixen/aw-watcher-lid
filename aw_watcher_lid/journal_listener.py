"""Journal-based listener for lid and suspend events (fallback when D-Bus unavailable)."""

import json
import logging
import subprocess
import threading
import time
from datetime import datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .lid import LidWatcher

logger = logging.getLogger(__name__)


class JournalListener:
    """Polls journalctl for lid and suspend events."""

    def __init__(self, watcher: "LidWatcher") -> None:
        """Initialize the journal listener.

        Args:
            watcher: The LidWatcher instance to notify of events
        """
        self.watcher = watcher
        self.running = False
        self.thread: threading.Thread | None = None
        self.poll_interval = watcher.config.get("journal_poll_interval", 60.0)

    def start(self) -> None:
        """Start polling the journal for events."""
        self.running = True
        self.thread = threading.Thread(target=self._poll_loop, daemon=True)
        self.thread.start()
        logger.info(f"Journal listener started (polling every {self.poll_interval}s)")

        # Keep main thread alive
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()

    def stop(self) -> None:
        """Stop polling the journal."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)

    def _poll_loop(self) -> None:
        """Main polling loop."""
        # Track last seen timestamp to avoid duplicates
        last_timestamp = datetime.now(timezone.utc)

        while self.running:
            try:
                self._check_journal(since=last_timestamp)
                last_timestamp = datetime.now(timezone.utc)
            except Exception as e:
                logger.error(f"Error polling journal: {e}")

            time.sleep(self.poll_interval)

    def _check_journal(self, since: datetime) -> None:
        """Check journal for lid and suspend events since given time.

        Args:
            since: Only check events after this time
        """
        # Format timestamp for journalctl
        since_str = since.strftime("%Y-%m-%d %H:%M:%S")

        # Query journalctl for relevant events
        # We look for:
        # - systemd-logind messages about lid state
        # - systemd messages about suspend/resume
        cmd = [
            "journalctl",
            "--since",
            since_str,
            "--output=json",
            "--no-pager",
            "-u",
            "systemd-logind",
            "-u",
            "systemd-suspend.service",
            "-u",
            "systemd-sleep.service",
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10, check=False)

            if result.returncode != 0:
                logger.warning(f"journalctl returned {result.returncode}")
                return

            # Parse JSON output (one JSON object per line)
            for line in result.stdout.strip().split("\n"):
                if not line:
                    continue

                try:
                    entry = json.loads(line)
                    self._process_journal_entry(entry)
                except json.JSONDecodeError:
                    logger.debug(f"Failed to parse journal entry: {line[:100]}")

        except subprocess.TimeoutExpired:
            logger.warning("journalctl command timed out")
        except FileNotFoundError:
            logger.error("journalctl not found - journal monitoring unavailable")
            self.running = False

    def _process_journal_entry(self, entry: dict) -> None:
        """Process a single journal entry.

        Args:
            entry: Parsed JSON journal entry
        """
        message = entry.get("MESSAGE", "")

        # Check for lid events
        if "Lid" in message:
            if "closed" in message.lower():
                logger.debug(f"Journal: lid closed - {message}")
                self.watcher.handle_lid_event("closed")
            elif "opened" in message.lower():
                logger.debug(f"Journal: lid opened - {message}")
                self.watcher.handle_lid_event("open")

        # Check for suspend events
        if "Suspending" in message or "suspend" in message.lower():
            logger.debug(f"Journal: suspending - {message}")
            self.watcher.handle_suspend_event("suspended")

        # Check for resume events
        if "Resumed" in message or "resume" in message.lower():
            logger.debug(f"Journal: resumed - {message}")
            self.watcher.handle_suspend_event("resumed")
