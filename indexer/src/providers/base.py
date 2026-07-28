"""Protocol definition for embedding providers."""

from typing import Protocol, runtime_checkable


@runtime_checkable
class ModelProvider(Protocol):
    """Provider protocol for direct embedding API clients."""

    def generate_embeddings(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings using direct API."""
        ...
