"""Tests for the command line entry point."""

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
