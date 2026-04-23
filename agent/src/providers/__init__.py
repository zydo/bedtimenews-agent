"""Provider abstraction system for LLM and embedding models.

This module provides a unified interface for using different LLM providers
(OpenAI, Gemini, Claude, etc.) through a plugin-like architecture.

Example usage:
    from src.providers import get_provider

    # Get provider (defaults to LLM_PROVIDER env var or 'openai')
    provider = get_provider()

    # Get chat model
    llm = provider.get_chat_model(model="gpt-4", temperature=0.7)

    # Get embeddings model (LangChain)
    embeddings = provider.get_embeddings_model(model="text-embedding-3-small")

    # Generate embeddings (direct API, for indexer)
    vectors = provider.generate_embeddings(["text1", "text2"])
"""

from .base import ChatModelProvider, EmbeddingsProvider, ModelProvider
from .factory import get_provider, list_providers, register_provider

# Import all provider implementations to register them
# The @register_provider decorator only executes when the module is imported
from . import openai  # noqa: F401

__all__ = [
    "ChatModelProvider",
    "EmbeddingsProvider",
    "ModelProvider",
    "get_provider",
    "list_providers",
    "register_provider",
]
