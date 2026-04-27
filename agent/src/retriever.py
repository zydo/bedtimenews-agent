"""Semantic retrieval service using PGVector integration."""

import logging
from concurrent.futures import ThreadPoolExecutor
from typing import List, cast

from tenacity import retry, stop_after_attempt, wait_exponential

from .cache import LRUCache, hash_query
from .models import ChunkResult, RetrieveRequest, RetrieveResponse
from .providers import get_provider
from .settings import settings
from .vector_db import search_similar_chunks

logger = logging.getLogger(__name__)


# Initialize provider (module-level singleton)
_provider = get_provider()


class _Retriever:
    """
    Internal retriever implementation.

    DO NOT instantiate directly. Use the singleton instance:
        from .retriever import retriever
    """

    def __init__(self) -> None:
        self._embeddings = _provider.get_embeddings_model(model=settings.embedding_model)
        self._result_cache = LRUCache(capacity=1000)

    def retrieve(self, request: RetrieveRequest) -> RetrieveResponse:
        """Perform semantic retrieval based on the request."""
        # Check cache first
        cache_key = hash_query(request.query, request.match_threshold, request.match_count)
        cached_result = self._result_cache.get(cache_key)
        if cached_result is not None:
            # Type assertion: cached result is always RetrieveResponse
            return cast(RetrieveResponse, cached_result)

        query_embedding = self._generate_embedding(request.query)

        documents = search_similar_chunks(
            query_embedding=query_embedding,
            match_threshold=request.match_threshold,
            match_count=request.match_count,
            include_text=request.include_text,
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

        Generates all embeddings in a single batch API call, then runs
        DB searches in parallel using a thread pool.
        """
        if not requests:
            return []

        # Batch generate all embeddings at once
        all_queries = [r.query for r in requests]
        all_embeddings = self._embeddings.embed_documents(all_queries)

        def _search_one(
            request: RetrieveRequest, query_embedding: List[float]
        ) -> RetrieveResponse:
            documents = search_similar_chunks(
                query_embedding=query_embedding,
                match_threshold=request.match_threshold,
                match_count=request.match_count,
                include_text=request.include_text,
            )
            chunk_results = self._map_chunk_results(documents, request)
            return RetrieveResponse(
                query=request.query,
                match_threshold=request.match_threshold,
                match_count=request.match_count,
                results=chunk_results,
            )

        if len(requests) == 1:
            return [_search_one(requests[0], all_embeddings[0])]

        with ThreadPoolExecutor(max_workers=min(len(requests), 4)) as executor:
            futures = [
                executor.submit(_search_one, req, emb)
                for req, emb in zip(requests, all_embeddings)
            ]
            return [f.result() for f in futures]

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for a text query with retry logic."""
        return self._embeddings.embed_query(text)


# Public singleton instance
retriever = _Retriever()
