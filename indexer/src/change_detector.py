"""Change detection for content files."""

import hashlib
from pathlib import Path
from typing import Set, Tuple

from .paths import BEDTIMENEWS_ARCHIVE_CONTENTS_DIR
from .vector_db import VectorDB


def detect_changes(current_files: Set[str]) -> Tuple[Set[str], Set[str], Set[str]]:
    """Detect added, modified, and deleted files."""
    with VectorDB() as db:
        indexed_files = set(db.get_indexed_files())

        added = set()
        modified = set()

        for md_file in current_files:
            if md_file not in indexed_files:
                added.add(md_file)
            else:
                history = db.get_indexing_history(md_file)
                if not history:
                    added.add(md_file)
                else:
                    current_hash = calculate_file_hash(md_file)
                    if history["content_hash"] != current_hash:
                        modified.add(md_file)

                indexed_files.discard(md_file)

        deleted = indexed_files

    return added, modified, deleted


def calculate_file_hash(md_file: str) -> str:
    """Calculate SHA256 hash of file content."""
    with open(BEDTIMENEWS_ARCHIVE_CONTENTS_DIR / md_file, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def get_doc_id(md_file: str) -> str:
    """Convert markdown file path to document ID."""
    return Path(md_file).with_suffix("").as_posix()
