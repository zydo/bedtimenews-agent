#!/bin/bash
# ============================================================================
# Postgres schema bootstrap for the RAG vector store.
#
# ⚠️  The embedding column dimension comes from EMBEDDING_DIM (.env), and MUST
# match the output dimension of the configured embedding model
# (EMBEDDING_PROVIDER / *_EMBEDDING_MODEL). Mismatch => inserts fail with
# "expected N dimensions, not M".
#
# This script runs ONLY when Postgres initializes an EMPTY data volume
# (docker-entrypoint-initdb.d) and every statement is CREATE ... IF NOT EXISTS.
# Changing EMBEDDING_DIM later does NOT alter an existing table. To switch the
# embedding model on an existing database, follow the "Changing the embedding
# model" runbook in indexer/README.md (ALTER column + re-embed).
# ============================================================================
set -euo pipefail

# Default matches Qwen/Qwen3-Embedding-4B (2560 dims). halfvec is used because
# pgvector HNSW supports up to 4000 dims for halfvec (vs. 2000 for full vector).
EMBEDDING_DIM="${EMBEDDING_DIM:-2560}"

echo "init.sh: creating rag schema with embedding halfvec(${EMBEDDING_DIM})"

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    -- Initialize pgvector extension
    CREATE EXTENSION IF NOT EXISTS vector;
    -- Create schema for RAG data
    CREATE SCHEMA IF NOT EXISTS rag;

    -- Main table for storing document chunks and their embeddings
    CREATE TABLE IF NOT EXISTS rag.document_chunks (
        id SERIAL PRIMARY KEY,
        chunk_id VARCHAR(255) UNIQUE NOT NULL,
        -- e.g., "main_901-1000_960_chunk_000" (full path with underscores)
        doc_id VARCHAR(255) NOT NULL,
        -- e.g., "main/901-1000/960" (full relative path without .md extension)
        chunk_index INTEGER NOT NULL,
        -- 0-based index within document
        heading TEXT,
        text TEXT NOT NULL,
        word_count INTEGER NOT NULL DEFAULT 0,
        -- Vector embedding; dimension parametrized via EMBEDDING_DIM (see header).
        embedding halfvec(${EMBEDDING_DIM}),
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT valid_chunk_index CHECK (chunk_index >= 0),
        CONSTRAINT valid_word_count CHECK (word_count >= 0)
    );
    CREATE INDEX IF NOT EXISTS idx_doc_id ON rag.document_chunks(doc_id);
    CREATE INDEX IF NOT EXISTS idx_chunk_id ON rag.document_chunks(chunk_id);
    -- HNSW approximate nearest-neighbor index (defaults m=16, ef_construction=64)
    CREATE INDEX IF NOT EXISTS idx_embedding_hnsw ON rag.document_chunks
        USING hnsw (embedding halfvec_cosine_ops);

    GRANT USAGE ON SCHEMA rag TO "$POSTGRES_USER";
    GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA rag TO "$POSTGRES_USER";
    GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA rag TO "$POSTGRES_USER";

    -- Indexing history: file-level status via content hashing (incremental loads)
    CREATE TABLE IF NOT EXISTS rag.indexing_history (
        id SERIAL PRIMARY KEY,
        file_path VARCHAR(500) UNIQUE NOT NULL,
        content_hash VARCHAR(64) NOT NULL,
        indexed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        last_modified TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );
    CREATE INDEX IF NOT EXISTS idx_indexing_history_file_path ON rag.indexing_history(file_path);
    CREATE INDEX IF NOT EXISTS idx_indexing_history_content_hash ON rag.indexing_history(content_hash);

    -- File actions: audit log of ADD/MODIFY/DELETE during scheduled runs
    CREATE TABLE IF NOT EXISTS rag.file_actions (
        id SERIAL PRIMARY KEY,
        file_path VARCHAR(500) NOT NULL,
        action_type VARCHAR(10) NOT NULL,
        content_hash VARCHAR(64),
        run_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        processed_at TIMESTAMP WITH TIME ZONE,
        CONSTRAINT valid_action_type CHECK (action_type IN ('ADD', 'MODIFY', 'DELETE'))
    );
    CREATE INDEX IF NOT EXISTS idx_file_actions_file_path ON rag.file_actions(file_path);
    CREATE INDEX IF NOT EXISTS idx_file_actions_timestamp ON rag.file_actions(run_timestamp);
    CREATE INDEX IF NOT EXISTS idx_file_actions_type ON rag.file_actions(action_type);
EOSQL

echo "init.sh: schema ready"
