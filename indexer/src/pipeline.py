"""Main content indexing pipeline.

This pipeline:
    1. Syncs latest content from git repository
    2. Detects added/modified/deleted files
    3. Loads, chunks, and stores content in vector database
    4. Tracks indexing history for incremental updates
"""

import logging

from .change_detector import calculate_file_hash, detect_changes, get_doc_id
from .chunker import chunk_document
from .document_loader import load_document
from .embeddings import generate_embeddings
from .file_scanner import scan_files
from .git_sync import sync_repository
from .models import Chunk
from .stats import collect_stats
from .vector_db import (
    close_connection_pool,
    delete_chunks,
    delete_indexing_history,
    insert_chunks,
    log_file_action,
    update_indexing_history,
)

logging.basicConfig(
    level=logging.INFO, format="[%(asctime)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)


def main():
    """Main entry point for content indexing pipeline."""

    try:
        logger.info("=" * 70)
        logger.info(" CONTENT INDEXING PIPELINE")
        logger.info("=" * 70)

        logger.info("Phase 1: Detecting changes")
        sync_repository()
        current_files = scan_files()
        added, modified, deleted = detect_changes(current_files)

        logger.info(f"Changes: +{len(added)} ~{len(modified)} -{len(deleted)}")

        if not added and not modified and not deleted:
            logger.info("No changes. Pipeline complete.")
            return

        logger.info("Phase 2: Processing changes")
        process_deletions(deleted)

        all_chunks, _ = process_content_changes(added, modified)

        if all_chunks:
            logger.info("Phase 3: Statistics")
            logger.info("-" * 70)
            stats = collect_stats(all_chunks)
            logger.info(f"Total documents:        {stats['total_documents']}")
            logger.info(f"Total chunks:           {stats['total_chunks']}")
            logger.info(f"Total tokens:           {stats['total_tokens']:,}")
            logger.info(f"Avg tokens per chunk:   {stats['avg_tokens_per_chunk']:.1f}")
            logger.info(f"Min tokens:             {stats['min_tokens']}")
            logger.info(f"Max tokens:             {stats['max_tokens']}")
            logger.info(f"Embedding model:        {stats['embedding_model']}")
            logger.info(f"Estimated API calls:    {stats['estimated_api_calls']}")

        logger.info("=" * 70)
        logger.info(" PIPELINE COMPLETE")
        logger.info("=" * 70)

    except Exception:
        logger.error("=" * 70)
        logger.error(" PIPELINE FAILED")
        logger.error("=" * 70)
        logger.exception("Pipeline error")
        raise
    finally:
        close_connection_pool()


def process_deletions(deleted_files: set[str]) -> None:
    """Process deleted files: remove chunks and history."""
    if not deleted_files:
        return
    logger.info(f"Processing {len(deleted_files)} deleted files")
    for md_file in deleted_files:
        doc_id = get_doc_id(md_file)
        delete_chunks(doc_id)
        delete_indexing_history(md_file)
        log_file_action(md_file, "DELETE", "")


def process_content_changes(
    added: set[str], modified: set[str]
) -> tuple[list[Chunk], list[dict]]:
    """
    Process added and modified files, committing each file independently.

    Each file is embedded, inserted, and recorded in indexing_history as its
    own unit of work. This keeps runs resumable: if the pipeline fails partway,
    already-processed files stay committed and are skipped on the next run,
    instead of discarding the whole batch (and its embedding API spend). It
    also bounds memory, since only one file's embeddings are held at a time.
    """
    files_to_process = []

    for md_file in added:
        doc_id = get_doc_id(md_file)
        files_to_process.append((md_file, doc_id, "ADD", False))

    for md_file in modified:
        doc_id = get_doc_id(md_file)
        files_to_process.append((md_file, doc_id, "MODIFY", True))

    if not files_to_process:
        return [], []

    total = len(files_to_process)
    logger.info(
        f"Processing {len(added)} added + {len(modified)} modified files "
        f"({total} total, per-file embed + insert)"
    )

    all_chunks: list[Chunk] = []
    file_metadata: list[dict] = []

    for i, (md_file, doc_id, action, should_delete) in enumerate(
        files_to_process, start=1
    ):
        # Replace existing chunks for modified files before re-inserting.
        if should_delete:
            delete_chunks(doc_id)

        content_hash = calculate_file_hash(md_file)
        document = load_document(doc_id)
        chunks = chunk_document(document)

        if chunks:
            texts = [chunk.text for chunk in chunks]
            embeddings = generate_embeddings(texts)
            insert_chunks(chunks, embeddings=embeddings)

        # Record progress only after chunks are durably inserted, so a crash
        # leaves this file marked unprocessed and it is retried next run.
        update_indexing_history(md_file, content_hash)
        log_file_action(md_file, action, content_hash)

        all_chunks.extend(chunks)
        file_metadata.append(
            {
                "md_file": md_file,
                "doc_id": doc_id,
                "action": action,
                "content_hash": content_hash,
                "chunk_count": len(chunks),
            }
        )

        logger.info(f"  [{i}/{total}] {md_file}: {len(chunks)} chunks ({action})")

    return all_chunks, file_metadata


if __name__ == "__main__":
    main()
