"""File scanning and configuration-based filtering."""

import logging
import os
from pathlib import Path
from typing import Set

import yaml

from .paths import BEDTIMENEWS_ARCHIVE_CONTENTS_DIR, INDEX_CONFIG_FILE

logger = logging.getLogger(__name__)


def scan_files() -> Set[str]:
    """Scan content directory and filter files based on config."""
    md_files = set()
    for md_file in BEDTIMENEWS_ARCHIVE_CONTENTS_DIR.rglob("*.md"):
        rel_path = md_file.relative_to(BEDTIMENEWS_ARCHIVE_CONTENTS_DIR).as_posix()
        md_files.add(rel_path)

    config = _load_config()

    filtered_files = set()
    for md_file in md_files:
        if _should_include_file(md_file, config):
            filtered_files.add(md_file)

    logger.info(f"Scanned: {len(md_files)} files, filtered: {len(filtered_files)}")
    return filtered_files


def _load_config() -> dict:
    """Load index configuration from YAML file."""
    try:
        with open(INDEX_CONFIG_FILE, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except FileNotFoundError as e:
        raise RuntimeError(f"Config file not found: {INDEX_CONFIG_FILE}") from e
    except yaml.YAMLError as e:
        raise RuntimeError(f"Error parsing config file: {INDEX_CONFIG_FILE}") from e


def _should_include_file(md_file: str, config: dict) -> bool:
    """Check if a file should be included based on config rules.

    Args:
        md_file: Relative path to markdown file
        config: Config rules for indexing

    Returns:
        True if file should be included, False otherwise
    """
    md_file_path = Path(md_file)

    # Check include patterns
    include_patterns = config.get("include", [])
    if include_patterns and not any(
        md_file_path.match(pattern) for pattern in include_patterns
    ):
        return False

    # Check exclude patterns
    exclude_patterns = config.get("exclude", [])
    if exclude_patterns and any(
        md_file_path.match(pattern) for pattern in exclude_patterns
    ):
        return False

    # Validate file size
    min_size = config.get("validation", {}).get("min_file_size", 0)
    max_size = config.get("validation", {}).get("max_file_size", 10485760)

    file_size = os.path.getsize(BEDTIMENEWS_ARCHIVE_CONTENTS_DIR / md_file)
    return min_size <= file_size <= max_size
