"""OpenAI provider implementation."""

import os
from typing import List

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from openai import OpenAI as OpenAIClient

from ..base import ModelProvider
from ..factory import register_provider


@register_provider("openai")
class OpenAIProvider(ModelProvider):
    """OpenAI provider implementation for both LangChain and direct API."""

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

    def get_chat_model(
        self,
        model: str,
        temperature: float = 0.7,
        **kwargs
    ) -> ChatOpenAI:
        """Get LangChain ChatOpenAI instance.

        Provider-specific kwargs:
            - reasoning_effort: For GPT-5 models ('low', 'medium', 'high')
            - max_tokens: Maximum tokens to generate
            - top_p: Nucleus sampling parameter
        """
        # Extract OpenAI-specific parameters
        openai_params = {}

        # Known OpenAI-specific parameters
        openai_specific = ['reasoning_effort', 'max_tokens', 'top_p']

        for key in openai_specific:
            if key in kwargs:
                openai_params[key] = kwargs.pop(key)

        return ChatOpenAI(
            model=model,
            temperature=temperature,
            # api_key is read from OPENAI_API_KEY env var automatically
            **openai_params
        )

    def get_embeddings_model(
        self,
        model: str,
        **kwargs
    ) -> OpenAIEmbeddings:
        """Get LangChain OpenAIEmbeddings instance."""
        return OpenAIEmbeddings(
            model=model,
            # api_key is read from OPENAI_API_KEY env var automatically
        )

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
