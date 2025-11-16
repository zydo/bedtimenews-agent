"""Database Utilities for RAG Vector Database

Usage (inside Docker container):
    docker compose exec indexer python -m src.debugger test
    docker compose exec indexer python -m src.debugger stats
    docker compose exec indexer python -m src.debugger history
    docker compose exec indexer python -m src.debugger history main/901-1000/960.md
    docker compose exec indexer python -m src.debugger recent --limit 20
    docker compose exec indexer python -m src.debugger inspect main/901-1000/960.md
    docker compose exec indexer python -m src.debugger logs
    docker compose exec indexer python -m src.debugger logs --lines 100
    docker compose exec indexer python -m src.debugger logs --all
    docker compose exec indexer python -m src.debugger clear
"""

import argparse
import logging
import shutil
import sys
from pathlib import Path
from typing import Optional

from .paths import BEDTIMENEWS_ARCHIVE_CONTENTS_DIR
from .vector_db import VectorDB

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def _cmd_test():
    """Test database connection."""
    with VectorDB() as db:
        if db.test_connection():
            logger.info("Database ready")
            return True
        else:
            logger.error("Database test failed")
            return False


def _cmd_stats():
    """Display database statistics."""
    logger.info("=" * 60)
    logger.info("Database Statistics")
    logger.info("=" * 60)

    with VectorDB() as db:
        stats = db.get_table_stats()
        logger.info(f"Total documents:        {stats['total_documents']}")
        logger.info(f"Total chunks:           {stats['total_chunks']}")
        logger.info("=" * 60)


def _cmd_history(file_path: Optional[str] = None):
    """Display indexing history."""
    with VectorDB() as db:
        if file_path:
            logger.info(f"Indexing history for: {file_path}")
            history = db.get_indexing_history(file_path)
            if history:
                logger.info(f"  Content hash:  {history['content_hash']}")
                logger.info(f"  Indexed at:    {history['indexed_at']}")
                logger.info(f"  Last modified: {history['last_modified']}")
            else:
                logger.info("  No history found")
        else:
            logger.info("All indexed files:")
            indexed_files = db.get_indexed_files()
            logger.info(f"Total: {len(indexed_files)} files")
            for i, file in enumerate(sorted(indexed_files)[:20], 1):
                logger.info(f"  {i}. {file}")
            if len(indexed_files) > 20:
                logger.info(f"  ... and {len(indexed_files) - 20} more")


def _cmd_recent(limit: int = 10):
    """Display recently processed files."""
    logger.info(f"Recent file actions (last {limit}):")
    with VectorDB() as db:
        rows = db.get_recent_file_actions(limit)
        if rows:
            for row in rows:
                logger.info(
                    f"  [{row['action_type']:8}] {row['file_path']} "
                    f"({row['processed_at']})"
                )
        else:
            logger.info("  No recent actions")


def _cmd_inspect(file_path: str):
    """Inspect a specific file's chunks."""
    logger.info(f"Inspecting: {file_path}")

    doc_id = Path(file_path).with_suffix("").as_posix()

    with VectorDB() as db:
        history = db.get_indexing_history(file_path)
        if history:
            logger.info(f"  Content hash:  {history['content_hash']}")
            logger.info(f"  Indexed at:    {history['indexed_at']}")
            logger.info(f"  Last modified: {history['last_modified']}")

        chunks = db.get_file_chunks(doc_id)
        if chunks:
            logger.info(f"  Chunks: {len(chunks)}")
            for chunk in chunks[:10]:
                emb = "EMB" if chunk["has_embedding"] else "---"
                heading = chunk["heading"] or "(no heading)"
                logger.info(
                    f"    [{chunk['chunk_index']:3}] {emb} {heading[:50]} "
                    f"({chunk['word_count']} words)"
                )
            if len(chunks) > 10:
                logger.info(f"    ... and {len(chunks) - 10} more chunks")
        else:
            logger.info("  No chunks found")


def _cmd_logs(lines: Optional[int] = None, show_all: bool = False):
    """Display scheduled cron run logs."""

    log_file = Path("/var/log/indexer/cron.log")
    if not log_file.exists():
        logger.info(
            "No cron logs yet. The log file will be created after the first scheduled run."
        )
        logger.info("Cron schedule: Check with 'cat /etc/cron.d/indexer'")
        return

    logger.info(f"Cron logs from: {log_file}")
    logger.info("=" * 60)

    try:
        with open(log_file, "r") as f:
            all_lines = f.readlines()

        if not all_lines:
            logger.info("Log file is empty")
            return

        if show_all:
            logger.info(f"Showing all {len(all_lines)} lines:")
            for line in all_lines:
                logger.info(line.rstrip())
        else:
            display_lines = lines if lines else 50
            start_idx = max(0, len(all_lines) - display_lines)
            actual_lines = len(all_lines) - start_idx

            logger.info(f"Showing last {actual_lines} lines (total: {len(all_lines)}):")
            for line in all_lines[start_idx:]:
                logger.info(line.rstrip())

    except Exception as e:
        logger.error(f"Failed to read log file: {e}")


def _cmd_clear(force: bool = False):
    """Clear all data from database and delete cloned git repository."""
    if not force:
        logger.warning("=" * 60)
        logger.warning("WARNING: This will delete ALL data from the database:")
        logger.warning("         - All chunks")
        logger.warning("         - All indexing history")
        logger.warning("         - All file action logs")
        logger.warning("         and remove the cloned git repository!")
        logger.warning("=" * 60)
        confirm = input("Type 'DELETE ALL' to confirm: ")
        if confirm != "DELETE ALL":
            logger.info("Cancelled")
            return

    with VectorDB() as db:
        db.clear_all_chunks()
        db.clear_indexing_history()
        db.clear_file_actions()

    if BEDTIMENEWS_ARCHIVE_CONTENTS_DIR.exists():
        shutil.rmtree(BEDTIMENEWS_ARCHIVE_CONTENTS_DIR)
        logger.info(f"Deleted repository: {BEDTIMENEWS_ARCHIVE_CONTENTS_DIR}")
    else:
        logger.info(f"Repository not found: {BEDTIMENEWS_ARCHIVE_CONTENTS_DIR}")


def main():
    """Main entry point for database utilities."""
    parser = argparse.ArgumentParser(
        description="RAG Vector Database Utilities",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    subparsers.add_parser("test", help="Test database connection")
    subparsers.add_parser("stats", help="Display database statistics")

    history_parser = subparsers.add_parser("history", help="Display indexing history")
    history_parser.add_argument("file", nargs="?", help="Specific file to inspect")

    recent_parser = subparsers.add_parser(
        "recent", help="Display recently processed files"
    )
    recent_parser.add_argument(
        "--limit", type=int, default=10, help="Number of recent files to show"
    )

    inspect_parser = subparsers.add_parser("inspect", help="Inspect a specific file")
    inspect_parser.add_argument("file", help="File path to inspect")

    logs_parser = subparsers.add_parser("logs", help="Display scheduled cron run logs")
    logs_parser.add_argument(
        "--lines", type=int, help="Number of lines to show (default: 50)"
    )
    logs_parser.add_argument("--all", action="store_true", help="Show all log lines")

    clear_parser = subparsers.add_parser("clear", help="Clear all chunks (DANGEROUS)")
    clear_parser.add_argument(
        "--force", action="store_true", help="Skip confirmation prompt"
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    try:
        if args.command == "test":
            success = _cmd_test()
            sys.exit(0 if success else 1)
        elif args.command == "stats":
            _cmd_stats()
        elif args.command == "history":
            _cmd_history(args.file if hasattr(args, "file") else None)
        elif args.command == "recent":
            _cmd_recent(args.limit)
        elif args.command == "inspect":
            _cmd_inspect(args.file)
        elif args.command == "logs":
            _cmd_logs(lines=args.lines, show_all=args.all)
        elif args.command == "clear":
            _cmd_clear(args.force)

    except Exception as e:
        logger.error(f"Command failed: {e}")
        import traceback

        logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
