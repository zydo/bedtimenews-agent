"""Vector Database Operations for RAG System.

Provides module-level functions for PostgreSQL + pgvector operations with connection pooling.
Follows the pattern from topicstreams/common/database.py.
"""

import logging
import threading
from functools import wraps
from typing import Any, Dict, List, Optional

import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.pool import ThreadedConnectionPool

from .settings import settings

logger = logging.getLogger(__name__)

# Module-level connection pool (singleton), guarded by a lock so concurrent
# first-callers don't each build a pool and orphan each other's connections.
_connection_pool: Optional[ThreadedConnectionPool] = None
_pool_lock = threading.Lock()

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
    """
    Get or create the connection pool singleton.

    Returns:
        ThreadedConnectionPool instance
    """
    global _connection_pool
    # Double-checked locking: fast path without the lock once initialized.
    if _connection_pool is None:
        with _pool_lock:
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
                except Exception:
                    logger.exception("Failed to create connection pool")
                    raise
    return _connection_pool


def close_connection_pool() -> None:
    """
    Close all connections in the pool.

    Call this during application shutdown for graceful cleanup.
    """
    global _connection_pool
    with _pool_lock:
        if _connection_pool is not None:
            try:
                _connection_pool.closeall()
                _connection_pool = None
                logger.info("Connection pool closed")
            except Exception:
                logger.exception("Error closing connection pool")


class _Connection:
    """Internal connection context manager."""

    def __init__(self) -> None:
        # Hold the exact pool we borrow from so the connection is always
        # returned to that same pool, even if the global is later swapped.
        self._pool = _get_connection_pool()
        self._conn = self._pool.getconn()
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

            self._pool.putconn(self._conn)
            logger.debug("Connection returned to pool")

        except Exception:
            logger.exception("Error returning connection to pool")
            # Try to close the connection if something went wrong
            try:
                if self._conn and not self._conn.closed:
                    self._conn.close()
            except Exception:
                pass

    def cursor(self):
        """Get the cursor for executing queries."""
        if self._cursor is None:
            raise RuntimeError("Cursor is only available within the context manager")
        return self._cursor


@retry_on_transient_error()
def search_similar_chunks(
    query_embedding: List[float],
    match_threshold: float = 0.7,
    match_count: int = 10,
    doc_id_filter: Optional[List[str]] = None,
    include_text: bool = True,
) -> List[Dict[str, Any]]:
    """
    Search for similar chunks using vector similarity.

    Args:
        query_embedding: embedding vector (2048 dims for Qwen/Qwen3-Embedding-4B)
        match_threshold: Minimum cosine similarity threshold
        match_count: Maximum number of results to return
        doc_id_filter: Optional list of doc_ids to restrict search
        include_text: Whether to include full text in results (False saves bandwidth for grading)

    Returns:
        List of matching chunks with similarity scores
    """
    query = f"""
        WITH similarities AS (
            SELECT DISTINCT ON (chunk_id)
                chunk_id,
                doc_id,
                chunk_index,
                heading,
                {'text,' if include_text else ''}
                word_count,
                1 - (embedding <=> %s::halfvec) as similarity
            FROM rag.document_chunks
            WHERE embedding IS NOT NULL
        )
        SELECT * FROM similarities
        WHERE similarity >= %s
    """

    params = [query_embedding, match_threshold]

    if doc_id_filter:
        placeholders = ",".join(["%s"] * len(doc_id_filter))
        query += f" AND doc_id IN ({placeholders})"
        params.extend(doc_id_filter)

    query += """
        ORDER BY similarity DESC, chunk_id
        LIMIT %s
    """
    params.append(match_count)

    with _Connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        results = cursor.fetchall()
        return [dict(row) for row in results]


@retry_on_transient_error()
def fetch_chunk_texts(chunk_ids: List[str]) -> Dict[str, str]:
    """
    Fetch full text for specific chunks by their IDs.

    Used to lazily load text only for relevant documents after grading.

    Args:
        chunk_ids: List of chunk_id values to fetch text for

    Returns:
        Dict mapping chunk_id to text content
    """
    if not chunk_ids:
        return {}

    placeholders = ",".join(["%s"] * len(chunk_ids))
    query = f"""
        SELECT chunk_id, text
        FROM rag.document_chunks
        WHERE chunk_id IN ({placeholders})
    """

    with _Connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, chunk_ids)
        return {row["chunk_id"]: row["text"] for row in cursor.fetchall()}
