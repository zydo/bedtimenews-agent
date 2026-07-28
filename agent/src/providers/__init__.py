"""Provider abstraction system for LLM and embedding models.

This module provides a unified interface for using different LLM providers
through a plugin-like architecture. Registered providers: openai, deepseek
(chat), siliconflow (embeddings). New providers can be added by subclassing
and decorating with @register_provider.

Example usage:
    from src.providers import get_provider

    # Get provider (defaults to LLM_PROVIDER env var or 'openai')
    provider = get_provider()

    # Get chat model
    llm = provider.get_chat_model(model="gpt-4", temperature=0.7)

    # Get embeddings model (LangChain)
    embeddings = provider.get_embeddings_model(model="text-embedding-3-small")

"""

# Import all provider implementations to register them
# The @register_provider decorator only executes when the module is imported
from . import (
    deepseek,  # noqa: F401
    openai,  # noqa: F401
    siliconflow,  # noqa: F401
)
from .base import ModelProvider
from .factory import get_provider, register_provider

__all__ = [
    "ModelProvider",
    "get_provider",
    "register_provider",
]
