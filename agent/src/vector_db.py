"""Vector Database Operations for RAG System.

Provides module-level functions for PostgreSQL + pgvector operations with connection pooling.
Follows the pattern from topicstreams/common/database.py.
"""

import logging
from functools import wraps
from typing import Any, Dict, List, Optional

import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.pool import ThreadedConnectionPool

from .settings import settings


logger = logging.getLogger(__name__)

# Module-level connection pool (singleton)
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
    """
    Get or create the connection pool singleton.

    Returns:
        ThreadedConnectionPool instance
    """
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
    """
    Close all connections in the pool.

    Call this during application shutdown for graceful cleanup.
    """
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
def search_similar_chunks(
    query_embedding: List[float],
    match_threshold: float = 0.7,
    match_count: int = 10,
    doc_id_filter: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """
    Search for similar chunks using vector similarity.

    Args:
        query_embedding: 1536-dimensional embedding vector
        match_threshold: Minimum cosine similarity threshold
        match_count: Maximum number of results to return
        doc_id_filter: Optional list of doc_ids to restrict search

    Returns:
        List of matching chunks with similarity scores
    """
    query = """
        WITH similarities AS (
            SELECT DISTINCT ON (chunk_id)
                chunk_id,
                doc_id,
                chunk_index,
                heading,
                text,
                word_count,
                1 - (embedding <=> %s::vector) as similarity
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
