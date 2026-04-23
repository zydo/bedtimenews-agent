"""Protocol definitions for LLM and embedding providers."""

from typing import List, Protocol, runtime_checkable


@runtime_checkable
class EmbeddingsProvider(Protocol):
    """Protocol for embedding providers compatible with direct API."""

    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for texts using direct API.

        This is used by the indexer which doesn't use LangChain.

        Args:
            texts: List of text strings to embed

        Returns:
            List of embedding vectors
        """
        ...


@runtime_checkable
class ModelProvider(Protocol):
    """Combined provider protocol for embeddings (indexer only needs embeddings)."""

    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using direct API."""
        ...
