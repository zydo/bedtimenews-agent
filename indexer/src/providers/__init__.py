"""Provider abstraction system for embedding models.

This module provides a unified interface for using different embedding providers
(OpenAI, Gemini, Claude, etc.) through a plugin-like architecture.

Example usage:
    from providers import get_provider

    # Get provider (defaults to LLM_PROVIDER env var or 'openai')
    provider = get_provider()

    # Generate embeddings (direct API)
    vectors = provider.generate_embeddings(["text1", "text2"])
"""

from .base import EmbeddingsProvider, ModelProvider
from .factory import get_provider, list_providers, register_provider

# Import all provider implementations to register them
# The @register_provider decorator only executes when the module is imported
from . import openai  # noqa: F401

__all__ = [
    "EmbeddingsProvider",
    "ModelProvider",
    "get_provider",
    "list_providers",
    "register_provider",
]
