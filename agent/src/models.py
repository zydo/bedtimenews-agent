"""Pydantic models for retrieval API."""

from typing import List, Optional

from pydantic import BaseModel, Field


# ============================================================================
# Chat API Models
# ============================================================================


class ChatRequest(BaseModel):
    """Request model for chat endpoint."""

    question: str = Field(
        ...,
        description="User's question or message",
        min_length=1,
        max_length=2000,
    )
    stream: bool = Field(
        default=False,
        description="Whether to stream the response",
    )


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""

    answer: str = Field(..., description="Generated answer")


# ============================================================================
# Retrieve API Models
# ============================================================================


class RetrieveRequest(BaseModel):
    """Request model for semantic search retrieval."""

    query: str = Field(
        ...,
        description="Semantic search query string",
        min_length=1,
    )
    match_threshold: float = Field(
        default=0.7,
        description="Cosine similarity threshold (0.0-1.0)",
        ge=0.0,
        le=1.0,
    )
    match_count: int = Field(
        default=10,
        description="Maximum number of results to return",
        ge=1,
        le=100,
    )
    doc_id_filter: Optional[List[str]] = Field(
        default=None,
        description="Optional list of doc_ids to restrict search to",
    )
    include_text: bool = Field(
        default=True,
        description="Whether to include full text in results",
    )
    include_heading: bool = Field(
        default=True,
        description="Whether to include heading in results",
    )


class ChunkResult(BaseModel):
    """Individual chunk result from retrieval."""

    chunk_id: str = Field(..., description="Unique chunk identifier")
    doc_id: str = Field(..., description="Document identifier")
    chunk_index: Optional[int] = Field(None, description="Chunk index within document")
    heading: Optional[str] = Field(None, description="Section heading")
    text: Optional[str] = Field(None, description="Chunk content")
    word_count: int = Field(..., description="Word count of chunk")
    similarity: float = Field(..., description="Cosine similarity score (0.0-1.0)")
    rank: int = Field(..., description="1-based rank in result list")


class RetrieveResponse(BaseModel):
    """Response model for semantic search retrieval."""

    query: str = Field(..., description="Query string used for search")
    match_threshold: float = Field(..., description="Similarity threshold used")
    match_count: int = Field(..., description="Maximum results requested")
    results: List[ChunkResult] = Field(
        default_factory=list,
        description="List of matching chunks",
    )
