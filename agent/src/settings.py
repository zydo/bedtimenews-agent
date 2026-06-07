"""Configuration management for the agent service."""

import os
from pydantic_settings import BaseSettings


def _get_required_env(key: str) -> str:
    """Get a required environment variable.

    Args:
        key: Environment variable name

    Returns:
        The environment variable value

    Raises:
        ValueError: If the environment variable is not set
    """
    value = os.environ.get(key)
    if not value:
        raise ValueError(f"Configuration error: {key} must be set in .env")
    return value


# Map provider names to their environment variable prefixes
_PROVIDER_ENV_PREFIX = {
    "openai": "OPENAI",
    "deepseek": "DEEPSEEK",
    "siliconflow": "SILICONFLOW",
}


class Settings(BaseSettings):
    """Application settings."""

    # Provider configuration
    # llm_provider drives chat models; embedding_provider drives embeddings.
    # They are decoupled so chat and embeddings can use different backends
    # (e.g. chat via DeepSeek, embeddings via SiliconFlow).
    llm_provider: str = os.environ.get("LLM_PROVIDER", "openai")
    embedding_provider: str = os.environ.get(
        "EMBEDDING_PROVIDER", os.environ.get("LLM_PROVIDER", "openai")
    )

    # Database configuration
    postgres_host: str = os.environ.get("POSTGRES_HOST", "postgres")
    postgres_port: int = int(os.environ.get("POSTGRES_PORT", "5432"))
    postgres_db: str = os.environ.get("POSTGRES_DB", "postgres_db")
    postgres_user: str = os.environ.get("POSTGRES_USER", "postgres_user")
    postgres_password: str = os.environ.get("POSTGRES_PASSWORD", "postgres_password")

    # Model configuration — resolved in __init__ from provider-prefixed env vars.
    # Chat models use {LLM_PROVIDER}_*; embeddings use {EMBEDDING_PROVIDER}_*.
    embedding_model: str = ""
    fast_model: str = ""
    generation_model: str = ""

    # Vector search configuration
    match_threshold: float = float(os.environ.get("MATCH_THRESHOLD", "0.4"))

    # Retrieval configuration
    retrieval_match_count: int = int(os.environ.get("RETRIEVAL_MATCH_COUNT", "30"))
    retrieval_top_k: int = int(os.environ.get("RETRIEVAL_TOP_K", "15"))
    grading_parallel_threshold: int = int(
        os.environ.get("GRADING_PARALLEL_THRESHOLD", "30")
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Resolve provider-specific env vars after pydantic sets the providers.
        chat_prefix = _PROVIDER_ENV_PREFIX.get(
            self.llm_provider, self.llm_provider.upper()
        )
        embedding_prefix = _PROVIDER_ENV_PREFIX.get(
            self.embedding_provider, self.embedding_provider.upper()
        )
        if not self.embedding_model:
            self.embedding_model = _get_required_env(
                f"{embedding_prefix}_EMBEDDING_MODEL"
            )
        if not self.fast_model:
            self.fast_model = _get_required_env(f"{chat_prefix}_FAST_MODEL")
        if not self.generation_model:
            self.generation_model = _get_required_env(
                f"{chat_prefix}_GENERATION_MODEL"
            )


settings = Settings()
