"""Entry point for aw-watcher-lid."""

import argparse
import logging
import signal
import sys

from .lid import LidWatcher

logger = logging.getLogger(__name__)


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="ActivityWatch watcher for lid events and system suspend/resume"
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    parser.add_argument(
        "--testing", action="store_true", help="Run in testing mode (don't connect to AW)"
    )

    args = parser.parse_args()

    # Set up logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    logger.info("Starting aw-watcher-lid...")

    # Create watcher
    watcher = LidWatcher(testing=args.testing)

    # Handle signals for graceful shutdown
    def signal_handler(signum: int, frame) -> None:  # type: ignore
        logger.info(f"Received signal {signum}, shutting down...")
        watcher.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        # Start the watcher (this will block)
        watcher.start()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
    finally:
        watcher.stop()


if __name__ == "__main__":
    main()
