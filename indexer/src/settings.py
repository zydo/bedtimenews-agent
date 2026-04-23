"""Configuration management for the indexer service."""

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


class Settings(BaseSettings):
    """Application settings for the indexer service."""

    # Provider configuration
    llm_provider: str = os.environ.get("LLM_PROVIDER", "openai")

    # Database configuration
    postgres_host: str = os.environ.get("POSTGRES_HOST", "postgres")
    postgres_port: int = int(os.environ.get("POSTGRES_PORT", "5432"))
    postgres_db: str = os.environ.get("POSTGRES_DB", "postgres_db")
    postgres_user: str = os.environ.get("POSTGRES_USER", "postgres_user")
    postgres_password: str = os.environ.get("POSTGRES_PASSWORD", "postgres_password")

    # Embedding configuration (provider-specific, no defaults)
    # TODO: Make env var requirements conditional based on LLM_PROVIDER
    # Currently always requires OpenAI env vars, but should be dynamic:
    # - If LLM_PROVIDER=openai: require OPENAI_* env vars
    # - If LLM_PROVIDER=gemini: require GEMINI_* env vars
    # - If LLM_PROVIDER=claude: require ANTHROPIC_* env vars
    # This requires refactoring _get_required_env() to accept provider prefix
    embedding_model: str = _get_required_env("OPENAI_EMBEDDING_MODEL")
    embedding_batch_size: int = int(os.environ.get("EMBEDDING_BATCH_SIZE", "20"))
    # API keys are read by provider implementations, not here
    # openai_api_key: str = os.environ["OPENAI_API_KEY"]

    # Indexer configuration
    indexer_cron_schedule: str = os.environ.get("INDEXER_CRON_SCHEDULE", "0 * * * *")


settings = Settings()
