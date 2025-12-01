"""
Vector Database Operations for RAG System

Provides the VectorDB class for PostgreSQL + pgvector operations with connection pooling.
"""

import logging
from typing import Any, Dict, List, Optional

from psycopg2.extras import RealDictCursor, execute_batch
from psycopg2.pool import ThreadedConnectionPool

from .models import Chunk
from .settings import settings


logger = logging.getLogger(__name__)

_connection_pool: Optional[ThreadedConnectionPool] = None


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


class VectorDB:
    """PostgreSQL + pgvector database with connection pooling."""

    def __init__(self):
        self.pool = _get_connection_pool()
        try:
            self._conn = self.pool.getconn()
            self._cursor = self._conn.cursor(cursor_factory=RealDictCursor)
            logger.debug("Connection acquired")
        except Exception as e:
            logger.error(f"Failed to get connection: {e}")
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

    def test_connection(self) -> bool:
        """Test database connection and pgvector extension."""
        try:
            self._cursor.execute("SELECT version();")
            version = self._cursor.fetchone()
            logger.info(
                f"PostgreSQL version: {version['version'] if version else "Unknown"}"
            )

            self._cursor.execute("SELECT * FROM pg_extension WHERE extname = 'vector';")
            result = self._cursor.fetchone()
            if result:
                logger.info(
                    f"pgvector extension installed (version: {result['extversion']})"
                )
            else:
                logger.error("pgvector extension not found")
                return False

            return True
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False

    def get_table_stats(self) -> Dict[str, Any]:
        """Get statistics about the document_chunks table."""
        self._cursor.execute(
            """
            SELECT
                COUNT(*) as total_chunks,
                COUNT(DISTINCT doc_id) as total_documents
            FROM rag.document_chunks;
        """
        )
        row = self._cursor.fetchone()
        return dict(row.items()) if row else {}

    def clear_all_chunks(self):
        """Delete all chunks from the database."""
        self._cursor.execute("DELETE FROM rag.document_chunks;")
        self._conn.commit()

    def delete_chunks(self, doc_id: str) -> int:
        """Delete all chunks for a specific document ID."""
        self._cursor.execute(
            "DELETE FROM rag.document_chunks WHERE doc_id = %s;", (doc_id,)
        )
        deleted_count = self._cursor.rowcount
        self._conn.commit()
        return deleted_count

    def insert_chunks(
        self,
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

        inserted = 0
        for i in range(0, len(chunk_data), batch_size):
            batch = chunk_data[i : i + batch_size]
            execute_batch(self._cursor, insert_query, batch)
            inserted += len(batch)
            logger.debug(f"Inserted {inserted}/{len(chunks)}")

        self._conn.commit()
        return inserted

    def update_indexing_history(self, file_path: str, content_hash: str) -> None:
        """Update or insert indexing history for a file."""
        self._cursor.execute(
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
        self._conn.commit()

    def delete_indexing_history(self, file_path: str) -> None:
        """Delete indexing history for a file."""
        self._cursor.execute(
            "DELETE FROM rag.indexing_history WHERE file_path = %s;",
            (file_path,),
        )
        self._conn.commit()

    def log_file_action(
        self, file_path: str, action_type: str, content_hash: str = ""
    ) -> None:
        """Log a file action (ADD, MODIFY, DELETE)."""
        if action_type not in ["ADD", "MODIFY", "DELETE"]:
            raise ValueError(
                f"Invalid action_type: {action_type}. Must be 'ADD', 'MODIFY', or 'DELETE'"
            )
        self._cursor.execute(
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
        self._conn.commit()

    def get_indexing_history(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Get indexing history for a file."""
        self._cursor.execute(
            """
            SELECT file_path, content_hash, indexed_at, last_modified
            FROM rag.indexing_history
            WHERE file_path = %s;
            """,
            (file_path,),
        )
        result = self._cursor.fetchone()
        return dict(result) if result else None

    def get_indexed_files(self) -> List[str]:
        """Get list of all indexed file paths."""
        self._cursor.execute("SELECT file_path FROM rag.indexing_history;")
        return [row["file_path"] for row in self._cursor.fetchall()]

    def get_recent_file_actions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent file actions."""
        self._cursor.execute(
            """
            SELECT file_path, action_type, processed_at
            FROM rag.file_actions
            ORDER BY processed_at DESC
            LIMIT %s;
            """,
            (limit,),
        )
        return [dict(row) for row in self._cursor.fetchall()]

    def get_file_chunks(self, doc_id: str) -> List[Dict[str, Any]]:
        """Get all chunks for a document."""
        self._cursor.execute(
            """
            SELECT chunk_id, chunk_index, heading, word_count,
                   embedding IS NOT NULL as has_embedding
            FROM rag.document_chunks
            WHERE doc_id = %s
            ORDER BY chunk_index;
            """,
            (doc_id,),
        )
        return [dict(row) for row in self._cursor.fetchall()]

    def clear_indexing_history(self) -> None:
        """Delete all indexing history records."""
        self._cursor.execute("DELETE FROM rag.indexing_history;")
        self._conn.commit()

    def clear_file_actions(self) -> None:
        """Delete all file action records."""
        self._cursor.execute("DELETE FROM rag.file_actions;")
        self._conn.commit()
