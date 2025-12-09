"""Vector Database Operations for RAG System.

Provides module-level functions for PostgreSQL + pgvector operations with connection pooling.
Follows the pattern from topicstreams/common/database.py.
"""

import logging
from functools import wraps
from typing import Any, Dict, List, Optional

import psycopg2
from psycopg2.extras import RealDictCursor, execute_batch
from psycopg2.pool import ThreadedConnectionPool

from .models import Chunk
from .settings import settings


logger = logging.getLogger(__name__)

_connection_pool: Optional[ThreadedConnectionPool] = None

# Transient errors that should trigger retry
TRANSIENT_ERRORS = (
    psycopg2.OperationalError,  # Connection issues, server restart
    psycopg2.InterfaceError,  # Connection lost during operation
)


def retry_on_transient_error(max_attempts: int = 3, delay_seconds: float = 0.1):
    """Decorator to retry database operations on transient failures.

    Args:
        max_attempts: Maximum number of retry attempts (default: 3)
        delay_seconds: Initial delay between retries in seconds (default: 0.1)
    """
    import time

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except TRANSIENT_ERRORS:
                    if attempt < max_attempts - 1:
                        # Exponential backoff
                        sleep_time = delay_seconds * (2**attempt)
                        time.sleep(sleep_time)
                    else:
                        # Final attempt failed, re-raise
                        raise

        return wrapper

    return decorator


def _get_connection_pool() -> ThreadedConnectionPool:
    """Get or create the connection pool singleton."""
    global _connection_pool
    if _connection_pool is None:
        try:
            _connection_pool = ThreadedConnectionPool(
                minconn=5,
                maxconn=20,
                host=settings.postgres_host,
                port=settings.postgres_port,
                database=settings.postgres_db,
                user=settings.postgres_user,
                password=settings.postgres_password,
                connect_timeout=10,
                keepalives=1,
                keepalives_idle=30,
                keepalives_interval=10,
                keepalives_count=5,
            )
            logger.info(
                "Connection pool created: minconn=5, maxconn=20 with keepalives"
            )
        except Exception as e:
            logger.error(f"Failed to create connection pool: {e}")
            raise
    return _connection_pool


def close_connection_pool() -> None:
    """Close all connections in the pool."""
    global _connection_pool
    if _connection_pool is not None:
        try:
            _connection_pool.closeall()
            _connection_pool = None
            logger.info("Connection pool closed")
        except Exception as e:
            logger.error(f"Error closing connection pool: {e}")


class _Connection:
    """Internal connection context manager."""

    def __init__(self) -> None:
        self._conn = _get_connection_pool().getconn()
        self._cursor = None

    def __enter__(self):
        self._cursor = self._conn.cursor(cursor_factory=RealDictCursor)
        return self

    def __exit__(self, exc_type, *_):
        try:
            if exc_type:
                self._conn.rollback()
                logger.debug("Transaction rolled back due to exception")
            else:
                self._conn.commit()
                logger.debug("Transaction committed")

            if self._cursor:
                self._cursor.close()

            _get_connection_pool().putconn(self._conn)
            logger.debug("Connection returned to pool")

        except Exception as e:
            logger.error(f"Error returning connection to pool: {e}")
            # Try to close the connection if something went wrong
            try:
                if self._conn and not self._conn.closed:
                    self._conn.close()
            except Exception:
                pass

    def cursor(self):
        """Get the cursor for executing queries."""
        return self._cursor


@retry_on_transient_error()
def test_connection() -> bool:
    """Test database connection and pgvector extension."""
    with _Connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()
        logger.info(
            f"PostgreSQL version: {version['version'] if version else 'Unknown'}"
        )

        cursor.execute("SELECT * FROM pg_extension WHERE extname = 'vector';")
        result = cursor.fetchone()
        if result:
            logger.info(
                f"pgvector extension installed (version: {result['extversion']})"
            )
        else:
            logger.error("pgvector extension not found")
            return False

        return True


@retry_on_transient_error()
def get_table_stats() -> Dict[str, Any]:
    """Get statistics about the document_chunks table."""
    with _Connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                COUNT(*) as total_chunks,
                COUNT(DISTINCT doc_id) as total_documents
            FROM rag.document_chunks;
        """
        )
        row = cursor.fetchone()
        return dict(row.items()) if row else {}


@retry_on_transient_error()
def clear_all_chunks() -> None:
    """Delete all chunks from the database."""
    with _Connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM rag.document_chunks;")


@retry_on_transient_error()
def delete_chunks(doc_id: str) -> int:
    """Delete all chunks for a specific document ID."""
    with _Connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM rag.document_chunks WHERE doc_id = %s;", (doc_id,)
        )
        return cursor.rowcount


@retry_on_transient_error()
def insert_chunks(
    chunks: List[Chunk],
    embeddings: List[List[float]] = [],
    batch_size: int = 100,
) -> int:
    """Insert chunks with optional embeddings."""
    if not chunks:
        return 0

    if embeddings and len(embeddings) != len(chunks):
        raise ValueError(
            f"Embeddings count ({len(embeddings)}) must match chunks count ({len(chunks)})"
        )

    has_embeddings = embeddings is not None
    logger.info(
        f"Inserting {len(chunks)} chunks"
        + (" with embeddings" if has_embeddings else "")
    )

    if has_embeddings:
        insert_query = """
            INSERT INTO rag.document_chunks (chunk_id, doc_id, chunk_index, heading, text, word_count, embedding)
            VALUES (%(chunk_id)s, %(doc_id)s, %(chunk_index)s, %(heading)s, %(text)s, %(word_count)s, %(embedding)s::vector)
            ON CONFLICT (chunk_id) DO NOTHING;
        """
    else:
        insert_query = """
            INSERT INTO rag.document_chunks (chunk_id, doc_id, chunk_index, heading, text, word_count)
            VALUES (%(chunk_id)s, %(doc_id)s, %(chunk_index)s, %(heading)s, %(text)s, %(word_count)s)
            ON CONFLICT (chunk_id) DO NOTHING;
        """

    chunk_data = []
    for i, chunk in enumerate(chunks):
        data = {
            "chunk_id": chunk.id,
            "doc_id": chunk.doc_id,
            "chunk_index": chunk.chunk_index,
            "heading": chunk.heading,
            "text": chunk.text,
            "word_count": chunk.word_count,
        }
        if has_embeddings:
            data["embedding"] = embeddings[i]
        chunk_data.append(data)

    with _Connection() as conn:
        cursor = conn.cursor()
        inserted = 0
        for i in range(0, len(chunk_data), batch_size):
            batch = chunk_data[i : i + batch_size]
            execute_batch(cursor, insert_query, batch)
            inserted += len(batch)
            logger.debug(f"Inserted {inserted}/{len(chunks)}")

        return inserted


@retry_on_transient_error()
def update_indexing_history(file_path: str, content_hash: str) -> None:
    """Update or insert indexing history for a file."""
    with _Connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO rag.indexing_history (file_path, content_hash)
            VALUES (%s, %s)
            ON CONFLICT (file_path) DO UPDATE
            SET content_hash = EXCLUDED.content_hash,
                indexed_at = CURRENT_TIMESTAMP,
                last_modified = CURRENT_TIMESTAMP;
            """,
            (file_path, content_hash),
        )


@retry_on_transient_error()
def delete_indexing_history(file_path: str) -> None:
    """Delete indexing history for a file."""
    with _Connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM rag.indexing_history WHERE file_path = %s;",
            (file_path,),
        )


@retry_on_transient_error()
def log_file_action(
    file_path: str, action_type: str, content_hash: str = ""
) -> None:
    """Log a file action (ADD, MODIFY, DELETE)."""
    if action_type not in ["ADD", "MODIFY", "DELETE"]:
        raise ValueError(
            f"Invalid action_type: {action_type}. Must be 'ADD', 'MODIFY', or 'DELETE'"
        )
    with _Connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO rag.file_actions (
                file_path,
                action_type,
                content_hash,
                processed_at
            )
            VALUES (%s, %s, %s, CURRENT_TIMESTAMP);
            """,
            (file_path, action_type, content_hash),
        )


@retry_on_transient_error()
def get_indexing_history(file_path: str) -> Optional[Dict[str, Any]]:
    """Get indexing history for a file."""
    with _Connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT file_path, content_hash, indexed_at, last_modified
            FROM rag.indexing_history
            WHERE file_path = %s;
            """,
            (file_path,),
        )
        result = cursor.fetchone()
        return dict(result) if result else None


@retry_on_transient_error()
def get_indexed_files() -> List[str]:
    """Get list of all indexed file paths."""
    with _Connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT file_path FROM rag.indexing_history;")
        return [row["file_path"] for row in cursor.fetchall()]


@retry_on_transient_error()
def get_recent_file_actions(limit: int = 10) -> List[Dict[str, Any]]:
    """Get recent file actions."""
    with _Connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT file_path, action_type, processed_at
            FROM rag.file_actions
            ORDER BY processed_at DESC
            LIMIT %s;
            """,
            (limit,),
        )
        return [dict(row) for row in cursor.fetchall()]


@retry_on_transient_error()
def get_file_chunks(doc_id: str) -> List[Dict[str, Any]]:
    """Get all chunks for a document."""
    with _Connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT chunk_id, chunk_index, heading, word_count,
                   embedding IS NOT NULL as has_embedding
            FROM rag.document_chunks
            WHERE doc_id = %s
            ORDER BY chunk_index;
            """,
            (doc_id,),
        )
        return [dict(row) for row in cursor.fetchall()]


@retry_on_transient_error()
def clear_indexing_history() -> None:
    """Delete all indexing history records."""
    with _Connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM rag.indexing_history;")


@retry_on_transient_error()
def clear_file_actions() -> None:
    """Delete all file action records."""
    with _Connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM rag.file_actions;")
