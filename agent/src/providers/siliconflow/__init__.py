"""SiliconFlow provider using the OpenAI-compatible endpoint.

SiliconFlow serves embedding models such as Qwen/Qwen3-Embedding-4B through an
OpenAI-compatible API. This provider supplies embeddings; chat methods are
inherited from OpenAIProvider but are not used here. The API key is read from
the SILICONFLOW_API_KEY environment variable.
"""

import os

from langchain_openai import OpenAIEmbeddings

from ..factory import register_provider
from ..openai import OpenAIProvider

SILICONFLOW_BASE_URL = "https://api.siliconflow.com/v1"


def _api_key() -> str:
    key = os.environ.get("SILICONFLOW_API_KEY")
    if not key:
        raise ValueError(
            "Configuration error: SILICONFLOW_API_KEY must be set in the environment"
        )
    return key


@register_provider("siliconflow")
class SiliconFlowProvider(OpenAIProvider):
    """SiliconFlow embeddings via OpenAI-compatible API."""

    def get_embeddings_model(self, model: str, **kwargs) -> OpenAIEmbeddings:
        """Get LangChain embeddings backed by SiliconFlow.

        check_embedding_ctx_length is disabled so inputs are sent as raw strings
        rather than tiktoken token ids, which SiliconFlow/Qwen expect.
        """
        return OpenAIEmbeddings(
            model=model,
            api_key=_api_key(),
            base_url=SILICONFLOW_BASE_URL,
            check_embedding_ctx_length=False,
        )
