from __future__ import annotations

import sys
import time
from pathlib import Path

from .config import load_config, setup_logging
from .runner import run_cycle


def main() -> int:
    try:
        config = load_config()
    except Exception as exc:
        print(f"Config error: {exc}", file=sys.stderr)
        return 1

    logger = setup_logging(config.log_level)
    state_path = Path(config.state_file)

    logger.info("Loaded %s passport(s)", len(config.targets))
    logger.info("Always email: %s", config.always_email)
    logger.info("Daily summary enabled: %s", config.daily_summary_enabled)
    logger.info("Error notify enabled: %s", config.error_notify_enabled)

    run_once = (
        str(__import__("os").getenv("RUN_ONCE", "true")).strip().lower()
        in {"1", "true", "yes", "on"}
    )

    if run_once:
        logger.info("Running in one-shot mode")
        run_cycle(config, state_path, logger)
        logger.info("One-shot run finished")
        return 0

    logger.info("Running in loop mode")
    while True:
        run_cycle(config, state_path, logger)
        logger.info("Sleeping for %s minute(s)", config.check_interval_minutes)
        try:
            time.sleep(max(1, config.check_interval_minutes) * 60)
        except KeyboardInterrupt:
            logger.info("Stopped by user")
            return 0


if __name__ == "__main__":
    raise SystemExit(main())