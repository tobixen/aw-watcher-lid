"""D-Bus listener for lid and suspend events via systemd-logind."""

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .lid import LidWatcher

logger = logging.getLogger(__name__)


class DbusListener:
    """Listens for lid and suspend events via D-Bus (systemd-logind)."""

    def __init__(self, watcher: "LidWatcher") -> None:
        """Initialize the D-Bus listener.

        Args:
            watcher: The LidWatcher instance to notify of events
        """
        self.watcher = watcher
        self.loop: Any | None = None
        self.bus: Any | None = None
        # The lid state logind last reported.  Kept apart from the watcher's
        # current_lid_state, which a suspend/resume event resets to None: a
        # lid check right after PrepareForSleep compared against that would
        # see a "change", end the suspend after milliseconds and record the
        # whole sleep as lid-open activity.
        self.last_lid_state: str | None = None

        # Import D-Bus libraries
        try:
            import dbus
            from dbus.mainloop.glib import DBusGMainLoop
            from gi.repository import GLib

            self.dbus = dbus
            self.DBusGMainLoop = DBusGMainLoop
            self.GLib = GLib
        except ImportError as e:
            raise ImportError(
                "D-Bus libraries not available. Install with: pip install dbus-python PyGObject"
            ) from e

    def start(self) -> None:
        """Start listening for D-Bus events."""
        # Set up D-Bus main loop
        self.DBusGMainLoop(set_as_default=True)

        # Connect to system bus
        self.bus = self.dbus.SystemBus()

        # Subscribe to PrepareForSleep signal
        self.bus.add_signal_receiver(
            self._on_prepare_for_sleep,
            signal_name="PrepareForSleep",
            dbus_interface="org.freedesktop.login1.Manager",
            bus_name="org.freedesktop.login1",
            path="/org/freedesktop/login1",
        )

        logger.info("D-Bus listener started, waiting for events...")

        # Check initial lid state
        self._check_lid_state()

        # Set up periodic lid state checking (every 5 seconds)
        # This is needed because D-Bus doesn't provide signals for lid state changes
        self.GLib.timeout_add_seconds(5, self._periodic_lid_check)

        # Start GLib main loop.  A stop() that lands before run() has its
        # quit() lost, so the loop checks once it is running.
        self.loop = self.GLib.MainLoop()
        self.GLib.idle_add(self._quit_if_stopped)
        self.loop.run()

    def _quit_if_stopped(self) -> bool:
        """Idle callback: quit the loop if the watcher was stopped meanwhile."""
        if self.watcher._stopped and self.loop:
            self.loop.quit()
        return False  # Run once

    def _periodic_lid_check(self) -> bool:
        """Periodic callback to check lid state.

        Returns:
            True to continue periodic calls
        """
        self._check_lid_state()
        return True  # Continue calling

    def stop(self) -> None:
        """Stop the D-Bus listener."""
        if self.loop:
            self.loop.quit()

    def _on_prepare_for_sleep(self, start: bool) -> None:
        """Handle PrepareForSleep signal from systemd-logind.

        Args:
            start: True when going to sleep, False when waking up
        """
        if start:
            logger.debug("System suspending")
            self.watcher.handle_suspend_event("suspended")
        else:
            logger.debug("System resuming")
            self.watcher.handle_suspend_event("resumed")

            # After resume, check lid state in case it changed during sleep
            self._check_lid_state(after_resume=True)

    def _check_lid_state(self, after_resume: bool = False) -> None:
        """Check current lid state via D-Bus.

        Args:
            after_resume: The resume ended the lid period, so a lid that is
                still closed is reported again
        """
        if self.bus is None:
            return

        try:
            # Get logind manager object
            manager_obj = self.bus.get_object("org.freedesktop.login1", "/org/freedesktop/login1")
            manager = self.dbus.Interface(
                manager_obj, dbus_interface="org.freedesktop.DBus.Properties"
            )

            # Check if lid is closed
            # Note: This property may not be available on all systems
            try:
                lid_closed = manager.Get("org.freedesktop.login1.Manager", "LidClosed")
                lid_state = "closed" if lid_closed else "open"
                logger.debug(f"Current lid state: {lid_state}")

                # A poll during a suspend (e.g. the lid close that triggered
                # it) leaves the reporting to the resume.  Otherwise, only send
                # an event when logind's lid state actually changed.
                if self.watcher.current_suspend_state == "suspended":
                    return
                if lid_state != self.last_lid_state or (after_resume and lid_state == "closed"):
                    self.last_lid_state = lid_state
                    self.watcher.handle_lid_event(lid_state)
            except self.dbus.exceptions.DBusException:
                # LidClosed property not available on this system
                logger.debug("LidClosed property not available")
        except Exception as e:
            logger.warning(f"Failed to check lid state: {e}")

    def _monitor_lid_events(self) -> None:
        """Monitor lid events via udev or acpi.

        This is an alternative approach if LidClosed property isn't available.
        For now, we rely on periodic checking after resume.
        """
        # TODO: Implement udev/acpi monitoring if needed
        pass
