"""OpenAI provider implementation for the indexer."""

import os
from typing import List

from openai import OpenAI as OpenAIClient

from ..base import ModelProvider
from ..factory import register_provider


@register_provider("openai")
class OpenAIProvider(ModelProvider):
    """OpenAI provider implementation using direct API."""

    def __init__(self) -> None:
        """Initialize OpenAI provider."""
        self._client = None

    @property
    def client(self) -> OpenAIClient:
        """Lazy-loaded OpenAI client for direct API calls."""
        if self._client is None:
            # Client reads OPENAI_API_KEY from environment automatically
            self._client = OpenAIClient()
        return self._client

    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using direct OpenAI API.

        Used by the indexer service.

        Args:
            texts: List of text strings to embed

        Returns:
            List of embedding vectors

        Raises:
            ValueError: If embedding model is not configured
        """
        # Get the model from provider-specific environment variable only
        # No defaults - user must explicitly configure
        model = os.environ.get("OPENAI_EMBEDDING_MODEL")

        if not model:
            raise ValueError(
                "Configuration error: OPENAI_EMBEDDING_MODEL must be set in .env"
            )

        response = self.client.embeddings.create(input=texts, model=model)
        return [item.embedding for item in response.data]
