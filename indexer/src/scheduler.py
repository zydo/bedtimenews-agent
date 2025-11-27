"""Cron scheduler for periodic pipeline execution."""

import logging
import os
import signal
import subprocess
import sys
import time

from .settings import settings

logger = logging.getLogger(__name__)

# Global flag for graceful shutdown
shutdown_requested = False


def schedule_cron():
    """Set up cron scheduler and keep container alive."""
    signal.signal(signal.SIGTERM, _signal_handler)
    signal.signal(signal.SIGINT, _signal_handler)

    logger.info("=" * 70)
    logger.info(" INDEXER SERVICE STARTING")
    logger.info("=" * 70)

    try:
        _setup_cron()
    except Exception as e:
        logger.error(f"Failed to set up cron: {e}")
        sys.exit(1)

    logger.info("=" * 70)
    logger.info(f" RUNNING - Schedule: {settings.indexer_cron_schedule}")
    logger.info("=" * 70)

    try:
        while not shutdown_requested:
            time.sleep(10)
    except KeyboardInterrupt:
        pass

    logger.info("Shutting down...")


def _signal_handler(signum, _frame):
    """Handle shutdown signals."""
    global shutdown_requested
    logger.info(f"Received signal {signum}")
    shutdown_requested = True


def _setup_cron():
    """Set up cron job for periodic pipeline execution."""
    cron_schedule = settings.indexer_cron_schedule
    logger.info(f"Setting up cron: {cron_schedule}")

    env_file = "/app/.env.cron"
    with open(env_file, "w") as f:
        for key, value in os.environ.items():
            if key not in ["_", "PWD", "SHLVL", "OLDPWD"]:
                escaped_value = value.replace('"', '\\"')
                f.write(f'export {key}="{escaped_value}"\n')
    os.chmod(env_file, 0o644)

    cron_command = f"cd /app && . {env_file} && python -m src.pipeline >> /var/log/indexer/cron.log 2>&1"
    crontab_entry = f"{cron_schedule} root {cron_command}\n"

    crontab_file = "/etc/cron.d/indexer"
    with open(crontab_file, "w") as f:
        f.write("# Indexer pipeline cron job\n")
        f.write("SHELL=/bin/bash\n")
        f.write("PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin\n")
        f.write("\n")
        f.write(crontab_entry)
    os.chmod(crontab_file, 0o644)

    os.makedirs("/var/log/indexer", exist_ok=True)
    subprocess.run(["cron"], check=True)
