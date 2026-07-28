"""Protocol definition for model providers."""

from typing import Any, Protocol, runtime_checkable

from langchain_core.language_models.chat_models import BaseChatModel


@runtime_checkable
class ModelProvider(Protocol):
    """Provider protocol for the agent's chat and embedding models."""

    def get_chat_model(
        self, model: str, temperature: float = 0.7, **kwargs
    ) -> BaseChatModel:
        """Get a LangChain-compatible chat model instance."""
        ...

    def get_embeddings_model(self, model: str, **kwargs) -> Any:
        """Get a LangChain-compatible embeddings model instance."""
        ...
