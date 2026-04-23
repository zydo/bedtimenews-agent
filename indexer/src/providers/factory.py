"""Provider factory and registry system."""

import os
from typing import Callable, Dict, List, Type

from .base import ModelProvider


# Global provider registry
_provider_registry: Dict[str, Type[ModelProvider]] = {}


def register_provider(name: str) -> Callable[[Type[ModelProvider]], Type[ModelProvider]]:
    """Decorator to register a provider class.

    Args:
        name: Provider name for registration

    Returns:
        Decorator function that registers and returns the provider class

    Usage:
        @register_provider("openai")
        class OpenAIProvider:
            ...
    """
    def decorator(provider_class: Type[ModelProvider]) -> Type[ModelProvider]:
        _provider_registry[name] = provider_class
        return provider_class
    return decorator


def get_provider(name: str | None = None) -> ModelProvider:
    """Get a provider instance by name.

    Args:
        name: Provider name (defaults to LLM_PROVIDER env var or 'openai')

    Returns:
        Provider instance

    Raises:
        ValueError: If provider is not registered
    """
    if name is None:
        name = os.environ.get("LLM_PROVIDER", "openai")

    provider_class = _provider_registry.get(name)
    if provider_class is None:
        available = ", ".join(_provider_registry.keys())
        raise ValueError(
            f"Unknown provider: {name}. Available providers: {available}"
        )

    # Instantiate - providers will read their own API keys from environment
    return provider_class()


def list_providers() -> List[str]:
    """List all registered provider names.

    Returns:
        List of provider names
    """
    return list(_provider_registry.keys())
