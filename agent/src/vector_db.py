"""
Vector Database Operations for RAG System

Provides the VectorDB class for PostgreSQL + pgvector operations with connection pooling.
"""

import logging
from typing import Any, Dict, List, Optional

from psycopg2.extras import RealDictCursor
from psycopg2.pool import ThreadedConnectionPool

from .settings import settings


logger = logging.getLogger(__name__)


# Module-level connection pool (singleton)
_connection_pool: Optional[ThreadedConnectionPool] = None


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


class VectorDB:
    """PostgreSQL + pgvector database with connection pooling."""

    def __init__(self):
        """Get a connection from the pool."""
        self.pool = _get_connection_pool()
        try:
            self._conn = self.pool.getconn()
            self._cursor = self._conn.cursor(cursor_factory=RealDictCursor)
            logger.debug("Connection acquired from pool")
        except Exception as e:
            logger.error(f"Failed to get connection from pool: {e}")
            raise

    def __enter__(self):
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

            # Return connection to pool instead of closing
            self.pool.putconn(self._conn)
            logger.debug("Connection returned to pool")

        except Exception as e:
            logger.error(f"Error returning connection to pool: {e}")
            # Try to close the connection if something went wrong
            try:
                if self._conn and not self._conn.closed:
                    self._conn.close()
            except Exception:
                pass

    def search_similar_chunks(
        self,
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

        try:
            self._cursor.execute(query, params)
            results = self._cursor.fetchall()
            return [dict(row) for row in results]
        except Exception as e:
            raise RuntimeError(f"Query execution error: {e}") from e
