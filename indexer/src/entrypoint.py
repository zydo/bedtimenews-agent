"""Docker container entrypoint for indexer service.

Usage:
    # Wait for cron schedule, do not run immediately (default)
    docker compose exec indexer python -m src.entrypoint

    # Run pipeline immediately, then set up cron scheduling
    docker compose exec indexer python -m src.entrypoint --run-immediately

    # Run pipeline once without scheduling (for manual execution)
    docker compose exec indexer python -m src.pipeline
"""

import argparse
import logging

from .pipeline import main as run_pipeline
from .scheduler import schedule_cron

logging.basicConfig(
    level=logging.INFO, format="[%(asctime)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
)

logger = logging.getLogger(__name__)

parser = argparse.ArgumentParser(
    description="Indexer service entrypoint",
    formatter_class=argparse.RawDescriptionHelpFormatter,
)
parser.add_argument(
    "--run-immediately",
    action="store_true",
    help="Run pipeline immediately on startup before scheduling (default: False)",
)


def main(run_immediately: bool):
    """Main entrypoint for indexer service.

    Args:
        run_immediately: If True, run pipeline immediately before setting up
                         cron scheduling. If False, wait for next cron schedule.
                         Default: False.
    """
    if run_immediately:
        logger.info("Running pipeline immediately...")
        try:
            run_pipeline()
        except Exception as e:
            logger.error(f"Pipeline execution failed: {e}")
            # Continue anyway to set up scheduled runs

    # Set up cron scheduler and keep container alive
    schedule_cron()


if __name__ == "__main__":
    args = parser.parse_args()
    main(run_immediately=args.run_immediately)
