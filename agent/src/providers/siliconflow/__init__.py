"""SiliconFlow provider using the OpenAI-compatible endpoint.

SiliconFlow serves embedding models such as Qwen/Qwen3-Embedding-4B through an
OpenAI-compatible API. This provider supplies embeddings; chat methods are
inherited from OpenAIProvider but are not used here. The API key is read from
the SILICONFLOW_API_KEY environment variable.
"""

import os

from langchain_openai import OpenAIEmbeddings
from openai import OpenAI as OpenAIClient

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

    @property
    def client(self) -> OpenAIClient:
        """Lazy-loaded client pointed at SiliconFlow."""
        if self._client is None:
            self._client = OpenAIClient(
                api_key=_api_key(), base_url=SILICONFLOW_BASE_URL
            )
        return self._client

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

    def generate_embeddings(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings using the direct SiliconFlow API."""
        model = os.environ.get("SILICONFLOW_EMBEDDING_MODEL")
        if not model:
            raise ValueError(
                "Configuration error: SILICONFLOW_EMBEDDING_MODEL must be set "
                "in the environment"
            )
        response = self.client.embeddings.create(input=texts, model=model)
        return [item.embedding for item in response.data]
