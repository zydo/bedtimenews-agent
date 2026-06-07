"""DeepSeek provider implementation using the OpenAI-compatible endpoint.

DeepSeek serves chat models through an OpenAI-compatible API but has no
embeddings endpoint, so embeddings are handled by a separate provider selected
via EMBEDDING_PROVIDER (see settings). The inherited embeddings methods are
unused when DeepSeek is the chat provider.
"""

import os

from langchain_openai import ChatOpenAI

from ..factory import register_provider
from ..openai import OpenAIProvider

DEEPSEEK_BASE_URL = "https://api.deepseek.com"


@register_provider("deepseek")
class DeepSeekProvider(OpenAIProvider):
    """DeepSeek chat via OpenAI-compatible API; embeddings delegate to OpenAI."""

    def get_chat_model(
        self, model: str, temperature: float = 0.7, **kwargs
    ) -> ChatOpenAI:
        """Get a LangChain ChatOpenAI instance pointed at DeepSeek.

        Provider-specific kwargs:
            - max_tokens: Maximum tokens to generate
            - top_p: Nucleus sampling parameter
        """
        api_key = os.environ.get("DEEPSEEK_API_KEY")
        if not api_key:
            raise ValueError(
                "Configuration error: DEEPSEEK_API_KEY must be set in .env"
            )

        openai_params = {}
        for key in ["max_tokens", "top_p"]:
            if key in kwargs:
                openai_params[key] = kwargs.pop(key)

        return ChatOpenAI(
            model=model,
            temperature=temperature,
            api_key=api_key,
            base_url=DEEPSEEK_BASE_URL,
            **openai_params,
        )
