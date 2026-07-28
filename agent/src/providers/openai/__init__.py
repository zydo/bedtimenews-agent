"""OpenAI provider implementation."""

from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from ..base import ModelProvider
from ..factory import register_provider


@register_provider("openai")
class OpenAIProvider(ModelProvider):
    """OpenAI provider implementation for LangChain."""

    def get_chat_model(
        self, model: str, temperature: float = 0.7, **kwargs
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
        openai_specific = ["reasoning_effort", "max_tokens", "top_p"]

        for key in openai_specific:
            if key in kwargs:
                openai_params[key] = kwargs.pop(key)

        return ChatOpenAI(
            model=model,
            temperature=temperature,
            # api_key is read from OPENAI_API_KEY env var automatically
            **openai_params,
        )

    def get_embeddings_model(self, model: str, **kwargs) -> OpenAIEmbeddings:
        """Get LangChain OpenAIEmbeddings instance."""
        return OpenAIEmbeddings(
            model=model,
            # api_key is read from OPENAI_API_KEY env var automatically
        )
