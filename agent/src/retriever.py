"""Semantic retrieval service using PGVector integration."""

from typing import List

from langchain_openai import OpenAIEmbeddings
from tenacity import retry, stop_after_attempt, wait_exponential

from .cache import LRUCache, hash_query
from .models import ChunkResult, RetrieveRequest, RetrieveResponse
from .settings import settings
from .vector_db import search_similar_chunks


class _Retriever:
    """
    Internal retriever implementation.

    DO NOT instantiate directly. Use the singleton instance:
        from .retriever import retriever
    """

    def __init__(self) -> None:
        self._embeddings = OpenAIEmbeddings(model=settings.embedding_model)
        self._result_cache = LRUCache(capacity=1000)

    def retrieve(self, request: RetrieveRequest) -> RetrieveResponse:
        """Perform semantic retrieval based on the request."""
        # Check cache first
        cache_key = hash_query(request.query, request.match_threshold, request.match_count)
        cached_result = self._result_cache.get(cache_key)
        if cached_result is not None:
            return cached_result

        query_embedding = self._generate_embedding(request.query)

        documents = search_similar_chunks(
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

        response = RetrieveResponse(
            query=request.query,
            match_threshold=request.match_threshold,
            match_count=request.match_count,
            results=results,
        )

        # Cache the result
        self._result_cache.put(cache_key, response)
        return response

    def retrieve_batch(self, requests: List[RetrieveRequest]) -> List[RetrieveResponse]:
        """
        Perform semantic retrieval for multiple queries efficiently.

        Generates all embeddings in a single batch API call for better performance.
        """
        if not requests:
            return []

        # Batch generate all embeddings at once
        all_queries = [r.query for r in requests]
        all_embeddings = self._embeddings.embed_documents(all_queries)

        results = []
        for request, query_embedding in zip(requests, all_embeddings):
            documents = search_similar_chunks(
                query_embedding=query_embedding,
                match_threshold=request.match_threshold,
                match_count=request.match_count,
            )

            chunk_results = []
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
                chunk_results.append(result)

            results.append(
                RetrieveResponse(
                    query=request.query,
                    match_threshold=request.match_threshold,
                    match_count=request.match_count,
                    results=chunk_results,
                )
            )

        return results

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for a text query with retry logic."""
        return self._embeddings.embed_query(text)


# Public singleton instance
retriever = _Retriever()
