-- Initialize pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;
-- Create schema for RAG data
CREATE SCHEMA IF NOT EXISTS rag;
-- Main table for storing document chunks and their embeddings
CREATE TABLE IF NOT EXISTS rag.document_chunks (
    -- Primary identifiers
    id SERIAL PRIMARY KEY,
    chunk_id VARCHAR(255) UNIQUE NOT NULL,
    -- e.g., "main_901-1000_960_chunk_000" (full path with underscores)
    doc_id VARCHAR(255) NOT NULL,
    -- e.g., "main/901-1000/960" (full relative path without .md extension)
    chunk_index INTEGER NOT NULL,
    -- 0-based index within document
    -- Content
    heading TEXT,
    -- Section heading for this chunk
    text TEXT NOT NULL,
    -- The actual chunk text
    word_count INTEGER NOT NULL DEFAULT 0,
    -- Number of words in this chunk
    -- Vector embedding (dimension configurable, default 1536 for OpenAI)
    embedding vector(1536),
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    -- Constraints
    CONSTRAINT valid_chunk_index CHECK (chunk_index >= 0),
    CONSTRAINT valid_word_count CHECK (word_count >= 0)
);
-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_doc_id ON rag.document_chunks(doc_id);
CREATE INDEX IF NOT EXISTS idx_chunk_id ON rag.document_chunks(chunk_id);
-- Create vector similarity search index (HNSW - Hierarchical Navigable Small World)
-- This index enables fast approximate nearest neighbor search
-- Using HNSW with default parameters (m=16, ef_construction=64)
CREATE INDEX IF NOT EXISTS idx_embedding_hnsw ON rag.document_chunks USING hnsw (embedding vector_cosine_ops);
-- Note: The username must be the same as ${POSTGRES_USER} from .env
GRANT USAGE ON SCHEMA rag TO postgres_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA rag TO postgres_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA rag TO postgres_user;
-- Indexing history table for tracking file-level indexing status using content hashing
-- This table enables incremental loading by detecting file changes based on content hashes
CREATE TABLE IF NOT EXISTS rag.indexing_history (
    id SERIAL PRIMARY KEY,
    file_path VARCHAR(500) UNIQUE NOT NULL,
    -- Relative path within the repository (e.g., "main/901-1000/960.md")
    content_hash VARCHAR(64) NOT NULL,
    -- SHA256 hash of file content for change detection
    indexed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_modified TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
-- Index for faster lookups by file_path
CREATE INDEX IF NOT EXISTS idx_indexing_history_file_path ON rag.indexing_history(file_path);
-- Index for faster content hash lookups
CREATE INDEX IF NOT EXISTS idx_indexing_history_content_hash ON rag.indexing_history(content_hash);
-- File actions table for tracking file operations during scheduled runs
-- Used for monitoring and debugging incremental loading operations
CREATE TABLE IF NOT EXISTS rag.file_actions (
    id SERIAL PRIMARY KEY,
    file_path VARCHAR(500) NOT NULL,
    -- Relative path within the repository (e.g., "main/901-1000/960.md")
    action_type VARCHAR(10) NOT NULL,
    -- 'ADD', 'MODIFY', 'DELETE' (based on content hashing)
    content_hash VARCHAR(64),
    -- SHA256 hash (NULL for DELETE)
    run_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    -- When the action was recorded
    processed_at TIMESTAMP WITH TIME ZONE,
    -- When the action was actually processed
    -- Constraints
    CONSTRAINT valid_action_type CHECK (action_type IN ('ADD', 'MODIFY', 'DELETE'))
);
-- Index for faster lookups by file_path and timestamp
CREATE INDEX IF NOT EXISTS idx_file_actions_file_path ON rag.file_actions(file_path);
CREATE INDEX IF NOT EXISTS idx_file_actions_timestamp ON rag.file_actions(run_timestamp);
CREATE INDEX IF NOT EXISTS idx_file_actions_type ON rag.file_actions(action_type);