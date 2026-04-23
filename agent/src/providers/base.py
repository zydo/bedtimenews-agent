"""Protocol definitions for LLM and embedding providers."""

from typing import Any, List, Protocol, runtime_checkable

from langchain_core.language_models.chat_models import BaseChatModel


@runtime_checkable
class ChatModelProvider(Protocol):
    """Protocol for chat model providers compatible with LangChain."""

    def get_chat_model(
        self,
        model: str,
        temperature: float = 0.7,
        **kwargs
    ) -> BaseChatModel:
        """Get a LangChain-compatible chat model instance.

        Args:
            model: Model identifier (e.g., 'gpt-4', 'gemini-pro')
            temperature: Sampling temperature
            **kwargs: Provider-specific parameters

        Returns:
            LangChain BaseChatModel instance
        """
        ...


@runtime_checkable
class EmbeddingsProvider(Protocol):
    """Protocol for embedding providers compatible with LangChain."""

    def get_embeddings_model(
        self,
        model: str,
        **kwargs
    ) -> Any:
        """Get a LangChain-compatible embeddings model instance.

        Args:
            model: Model identifier (e.g., 'text-embedding-3-small')
            **kwargs: Provider-specific parameters

        Returns:
            LangChain embeddings instance (e.g., OpenAIEmbeddings)
        """
        ...

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
    """Combined provider protocol for both chat and embeddings."""

    def get_chat_model(
        self,
        model: str,
        temperature: float = 0.7,
        **kwargs
    ) -> BaseChatModel:
        """Get a LangChain-compatible chat model instance."""
        ...

    def get_embeddings_model(
        self,
        model: str,
        **kwargs
    ) -> Any:
        """Get a LangChain-compatible embeddings model instance."""
        ...

    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using direct API."""
        ...
