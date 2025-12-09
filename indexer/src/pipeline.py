"""Main content indexing pipeline.

This pipeline:
    1. Syncs latest content from git repository
    2. Detects added/modified/deleted files
    3. Loads, chunks, and stores content in vector database
    4. Tracks indexing history for incremental updates
"""

import logging
from typing import List, Set

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
        chunks = []
        chunks.extend(process_added(added))
        chunks.extend(process_modified(modified))
        chunks.extend(process_deleted(deleted))

        if chunks:
            logger.info("Phase 3: Statistics")
            logger.info("-" * 70)
            stats = collect_stats(chunks)
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


def process_added(md_files: Set[str]) -> List[Chunk]:
    """Process newly added markdown files."""
    if not md_files:
        return []
    logger.info(f"Processing {len(md_files)} added files")
    chunks = []
    for md_file in md_files:
        chunks.extend(_process_file(md_file, "ADD", should_delete_chunks=False))
    return chunks


def process_modified(md_files: Set[str]) -> List[Chunk]:
    """Process modified markdown files."""
    if not md_files:
        return []
    logger.info(f"Processing {len(md_files)} modified files")
    chunks = []
    for md_file in md_files:
        chunks.extend(_process_file(md_file, "MODIFY", should_delete_chunks=True))
    return chunks


def process_deleted(md_files: Set[str]) -> List[Chunk]:
    """Process deleted markdown files."""
    if not md_files:
        return []
    logger.info(f"Processing {len(md_files)} deleted files")
    chunks = []
    for md_file in md_files:
        chunks.extend(_process_file(md_file, "DELETE", should_delete_chunks=True))
    return chunks


def _process_file(
    md_file: str,
    action: str,
    should_delete_chunks: bool = False,
) -> List[Chunk]:
    """Common processing logic for all file actions."""
    logger.debug(f"{action}: {md_file}")
    doc_id = get_doc_id(md_file)

    if should_delete_chunks:
        delete_chunks(doc_id)

    content_hash = ""
    chunks = []
    if action != "DELETE":
        content_hash = calculate_file_hash(md_file)
        document = load_document(doc_id)
        chunks = chunk_document(document)
        texts = [chunk.text for chunk in chunks]
        embeddings = generate_embeddings(texts)
        insert_chunks(chunks, embeddings=embeddings)
        logger.info(f"  {md_file}: {len(chunks)} chunks, {len(embeddings)} embeddings")

    if action == "DELETE":
        delete_indexing_history(md_file)
    else:
        update_indexing_history(md_file, content_hash)

    log_file_action(md_file, action, content_hash)
    return chunks


if __name__ == "__main__":
    main()
