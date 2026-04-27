"""Main content indexing pipeline.

This pipeline:
    1. Syncs latest content from git repository
    2. Detects added/modified/deleted files
    3. Loads, chunks, and stores content in vector database
    4. Tracks indexing history for incremental updates
"""

import logging
from typing import List, Set, Tuple

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

        all_chunks, file_metadata = process_content_changes(added, modified)

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

    except Exception as e:
        logger.error("=" * 70)
        logger.error(" PIPELINE FAILED")
        logger.error("=" * 70)
        logger.error(f"Error: {e}")
        import traceback

        logger.error(traceback.format_exc())
        raise
    finally:
        close_connection_pool()


def process_deletions(deleted_files: Set[str]) -> None:
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
    added: Set[str], modified: Set[str]
) -> Tuple[List[Chunk], List[dict]]:
    """
    Process added and modified files with batched embedding generation.

    Instead of generating embeddings per-file, collects all chunks across
    files first, then generates embeddings in one batch for fewer API calls.
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

    logger.info(
        f"Processing {len(added)} added + {len(modified)} modified files "
        f"({len(files_to_process)} total, batched embeddings)"
    )

    # Phase 1: Delete old chunks for modified files, load and chunk all files
    all_chunks: List[Chunk] = []
    file_metadata: List[dict] = []

    for md_file, doc_id, action, should_delete in files_to_process:
        if should_delete:
            delete_chunks(doc_id)

        content_hash = calculate_file_hash(md_file)
        document = load_document(doc_id)
        chunks = chunk_document(document)
        all_chunks.extend(chunks)

        file_metadata.append({
            "md_file": md_file,
            "doc_id": doc_id,
            "action": action,
            "content_hash": content_hash,
            "chunk_count": len(chunks),
        })

        logger.debug(f"  {md_file}: {len(chunks)} chunks")

    # Phase 2: Generate embeddings in one batch across all files
    if all_chunks:
        logger.info(f"Generating embeddings for {len(all_chunks)} chunks in batch")
        texts = [chunk.text for chunk in all_chunks]
        embeddings = generate_embeddings(texts)

        # Phase 3: Insert all chunks with embeddings
        insert_chunks(all_chunks, embeddings=embeddings)

    # Phase 4: Update history and log actions
    for meta in file_metadata:
        update_indexing_history(meta["md_file"], meta["content_hash"])
        log_file_action(meta["md_file"], meta["action"], meta["content_hash"])
        logger.info(
            f"  {meta['md_file']}: {meta['chunk_count']} chunks ({meta['action']})"
        )

    return all_chunks, file_metadata


if __name__ == "__main__":
    main()
