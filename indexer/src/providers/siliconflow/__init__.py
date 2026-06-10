"""SiliconFlow embeddings provider for the indexer (OpenAI-compatible).

SiliconFlow serves embedding models such as Qwen/Qwen3-Embedding-4B through an
OpenAI-compatible API. The API key is read from the SILICONFLOW_API_KEY
environment variable and the model from SILICONFLOW_EMBEDDING_MODEL.
"""

import os
from typing import List

from openai import OpenAI as OpenAIClient

from ..factory import register_provider
from ..openai import OpenAIProvider

SILICONFLOW_BASE_URL = "https://api.siliconflow.com/v1"


@register_provider("siliconflow")
class SiliconFlowProvider(OpenAIProvider):
    """SiliconFlow embeddings via OpenAI-compatible API."""

    @property
    def client(self) -> OpenAIClient:
        """Lazy-loaded client pointed at SiliconFlow."""
        if self._client is None:
            api_key = os.environ.get("SILICONFLOW_API_KEY")
            if not api_key:
                raise ValueError(
                    "Configuration error: SILICONFLOW_API_KEY must be set "
                    "in the environment"
                )
            self._client = OpenAIClient(api_key=api_key, base_url=SILICONFLOW_BASE_URL)
        return self._client

    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using the direct SiliconFlow API."""
        model = os.environ.get("SILICONFLOW_EMBEDDING_MODEL")
        if not model:
            raise ValueError(
                "Configuration error: SILICONFLOW_EMBEDDING_MODEL must be set "
                "in the environment"
            )
        response = self.client.embeddings.create(input=texts, model=model)
        return [item.embedding for item in response.data]
