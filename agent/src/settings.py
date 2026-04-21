"""Configuration management for the agent service."""

import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    # Database configuration
    postgres_host: str = os.environ.get("POSTGRES_HOST", "postgres")
    postgres_port: int = int(os.environ.get("POSTGRES_PORT", "5432"))
    postgres_db: str = os.environ.get("POSTGRES_DB", "postgres_db")
    postgres_user: str = os.environ.get("POSTGRES_USER", "postgres_user")
    postgres_password: str = os.environ.get("POSTGRES_PASSWORD", "postgres_password")

    # langchan_openai.ChatOpenAI will automatically read OPENAI_API_KEY env, we can omitted it.
    # openai_api_key: str = os.environ["OPENAI_API_KEY"]

    # Embedding configuration
    embedding_model: str = os.environ.get("EMBEDDING_MODEL", "text-embedding-3-small")

    # Chat models configuration
    fast_model: str = os.environ.get("FAST_MODEL", "gpt-5-nano")
    generation_model: str = os.environ.get("GENERATION_MODEL", "gpt-5-mini")

    # Vector search configuration
    match_threshold: float = float(os.environ.get("MATCH_THRESHOLD", "0.4"))


settings = Settings()
