"""Configuration management for aw-watcher-lid."""

import tomllib
from pathlib import Path

DEFAULT_CONFIG = """
# Enable boot gap detection
enable_boot_detection = true

# Boot gap threshold (seconds)
# Gaps longer than this are recorded as system downtime
boot_gap_threshold = 300.0

# Polling interval when using journal fallback (seconds)
journal_poll_interval = 60.0
""".strip()


def get_config_path() -> Path:
    """Get the configuration file path."""
    config_dir = Path.home() / ".config" / "aw-watcher-lid"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir / "config.toml"


def load_config() -> dict:
    """Load configuration from file or create default."""
    config_path = get_config_path()

    if not config_path.exists():
        # Create default config
        config_path.write_text(DEFAULT_CONFIG)
        return tomllib.loads(DEFAULT_CONFIG)

    with open(config_path, "rb") as f:
        return tomllib.load(f)
