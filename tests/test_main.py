"""Tests for the command line entry point."""

import subprocess
import sys

import pytest

from aw_watcher_lid import __version__
from aw_watcher_lid.__main__ import main


@pytest.mark.parametrize("flag", ["--version", "-V"])
def test_version_flag(
    flag: str, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """--version / -V prints the package version and exits cleanly."""
    monkeypatch.setattr("sys.argv", ["aw-watcher-lid", flag])
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 0
    assert capsys.readouterr().out.strip() == f"aw-watcher-lid {__version__}"
    assert __version__ != "0.1.0"


SIGTERM_IN_GLIB_LOOP = """
import os, signal, sys
from gi.repository import GLib
import aw_watcher_lid.__main__ as m

class FakeWatcher:
    def __init__(self, testing):
        self.loop = GLib.MainLoop()
        self.stopped = False
    def start(self):
        GLib.timeout_add(50, lambda: os.kill(os.getpid(), signal.SIGTERM) and False)
        self.loop.run()
    def stop(self):
        if not self.stopped:
            self.stopped = True
            print("stopped", flush=True)
        self.loop.quit()

m.LidWatcher = FakeWatcher
sys.argv = ["aw-watcher-lid"]
m.main()
print("returned", flush=True)
"""


def test_sigterm_in_glib_loop_stops_watcher() -> None:
    """SIGTERM while the GLib main loop runs must still close the watcher cleanly.

    Runs in a subprocess: a SystemExit raised inside a GLib callback kills the
    interpreter outright, which would take pytest down with it.
    """
    result = subprocess.run(
        [sys.executable, "-c", SIGTERM_IN_GLIB_LOOP],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.stdout.split() == ["stopped", "returned"], result.stderr
