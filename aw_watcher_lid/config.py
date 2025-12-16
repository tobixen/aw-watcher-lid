"""Configuration management for aw-watcher-lid."""

from aw_core.config import load_config_toml

DEFAULT_CONFIG = """
# Enable boot gap detection
enable_boot_detection = true

# Boot gap threshold (seconds)
# Gaps longer than this are recorded as system downtime
boot_gap_threshold = 300.0

# Polling interval when using journal fallback (seconds)
journal_poll_interval = 60.0
""".strip()


def load_config() -> dict:
    """Load configuration using ActivityWatch standard approach.

    Config location: ~/.config/activitywatch/aw-watcher-lid/aw-watcher-lid.toml
    """
    return load_config_toml("aw-watcher-lid", DEFAULT_CONFIG)
