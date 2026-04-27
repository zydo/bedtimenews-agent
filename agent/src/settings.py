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


class Settings(BaseSettings):
    """Application settings."""

    # Provider configuration
    llm_provider: str = os.environ.get("LLM_PROVIDER", "openai")

    # Database configuration
    postgres_host: str = os.environ.get("POSTGRES_HOST", "postgres")
    postgres_port: int = int(os.environ.get("POSTGRES_PORT", "5432"))
    postgres_db: str = os.environ.get("POSTGRES_DB", "postgres_db")
    postgres_user: str = os.environ.get("POSTGRES_USER", "postgres_user")
    postgres_password: str = os.environ.get("POSTGRES_PASSWORD", "postgres_password")

    # API keys are read by provider implementations, not here
    # openai_api_key: str = os.environ["OPENAI_API_KEY"]

    # TODO: Make env var requirements conditional based on LLM_PROVIDER
    # Currently always requires OpenAI env vars, but should be dynamic:
    # - If LLM_PROVIDER=openai: require OPENAI_* env vars
    # - If LLM_PROVIDER=gemini: require GEMINI_* env vars
    # - If LLM_PROVIDER=claude: require ANTHROPIC_* env vars
    # This requires refactoring _get_required_env() to accept provider prefix

    # Embedding configuration (provider-specific, no defaults)
    embedding_model: str = _get_required_env("OPENAI_EMBEDDING_MODEL")

    # Chat models configuration (provider-specific, no defaults)
    fast_model: str = _get_required_env("OPENAI_FAST_MODEL")
    generation_model: str = _get_required_env("OPENAI_GENERATION_MODEL")

    # Vector search configuration
    match_threshold: float = float(os.environ.get("MATCH_THRESHOLD", "0.4"))

    # Retrieval configuration
    retrieval_match_count: int = int(os.environ.get("RETRIEVAL_MATCH_COUNT", "30"))
    retrieval_top_k: int = int(os.environ.get("RETRIEVAL_TOP_K", "15"))
    grading_parallel_threshold: int = int(os.environ.get("GRADING_PARALLEL_THRESHOLD", "30"))


settings = Settings()
