"""Git repository synchronization."""

import logging
import subprocess
from pathlib import Path
from typing import List, Optional, Tuple

from .paths import BEDTIMENEWS_ARCHIVE_CONTENTS_DIR

logger = logging.getLogger(__name__)

BEDTIMENEWS_ARCHIVE_CONTENTS_REPO_URL = (
    "https://github.com/bedtimenews/bedtimenews-archive-contents.git"
)


def sync_repository() -> None:
    """Get a local copy of the latest git repo content of bedtimenews-archive-contents."""
    if not (BEDTIMENEWS_ARCHIVE_CONTENTS_DIR / ".git").exists():
        logger.info(f"Cloning repository to {BEDTIMENEWS_ARCHIVE_CONTENTS_DIR}")
        success, output = _run_command(
            [
                "git",
                "clone",
                BEDTIMENEWS_ARCHIVE_CONTENTS_REPO_URL,
                str(BEDTIMENEWS_ARCHIVE_CONTENTS_DIR),
            ],
            BEDTIMENEWS_ARCHIVE_CONTENTS_DIR.parent,
        )
        if not success:
            logger.error(f"Failed to clone: {output}")
            raise RuntimeError(f"Failed to clone repository: {output}")
    else:
        success, output = _run_command(
            ["git", "pull", "origin", "main"], BEDTIMENEWS_ARCHIVE_CONTENTS_DIR
        )
        if not success:
            logger.error(f"Failed to pull: {output}")
            raise RuntimeError(f"Failed to pull changes: {output}")


def _run_command(cmd: List[str], cwd: Optional[Path] = None) -> Tuple[bool, str]:
    """Run a shell command and return success status and output."""
    try:
        result = subprocess.run(
            cmd, cwd=cwd, capture_output=True, text=True, check=False
        )
        return result.returncode == 0, result.stdout.strip()
    except Exception as e:
        return False, str(e)
