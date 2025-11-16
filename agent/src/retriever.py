"""Semantic retrieval service using PGVector integration."""

from typing import List

from langchain_openai import OpenAIEmbeddings
from tenacity import retry, stop_after_attempt, wait_exponential

from .models import ChunkResult, RetrieveRequest, RetrieveResponse
from .settings import settings
from .vector_db import VectorDB


class _Retriever:
    """
    Internal retriever implementation.

    DO NOT instantiate directly. Use the singleton instance:
        from .retriever import retriever
    """

    def __init__(self) -> None:
        self._embeddings = OpenAIEmbeddings(model=settings.embedding_model)

    def retrieve(self, request: RetrieveRequest) -> RetrieveResponse:
        """Perform semantic retrieval based on the request."""
        query_embedding = self._generate_embedding(request.query)

        with VectorDB() as db:
            documents = db.search_similar_chunks(
                query_embedding=query_embedding,
                match_threshold=request.match_threshold,
                match_count=request.match_count,
            )

        results = []
        for rank, doc in enumerate(documents, start=1):
            result = ChunkResult(
                chunk_id=doc["chunk_id"],
                doc_id=doc["doc_id"],
                chunk_index=doc.get("chunk_index"),
                heading=doc.get("heading") if request.include_heading else None,
                text=doc["text"] if request.include_text else None,
                word_count=doc["word_count"],
                similarity=round(doc["similarity"], 4),
                rank=rank,
            )
            results.append(result)

        return RetrieveResponse(
            query=request.query,
            match_threshold=request.match_threshold,
            match_count=request.match_count,
            results=results,
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for a text query with retry logic."""
        return self._embeddings.embed_query(text)


# Public singleton instance
retriever = _Retriever()
