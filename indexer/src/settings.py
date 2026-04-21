"""Configuration management for the indexer service."""

import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings for the indexer service."""

    # Database configuration
    postgres_host: str = os.environ.get("POSTGRES_HOST", "postgres")
    postgres_port: int = int(os.environ.get("POSTGRES_PORT", "5432"))
    postgres_db: str = os.environ.get("POSTGRES_DB", "postgres_db")
    postgres_user: str = os.environ.get("POSTGRES_USER", "postgres_user")
    postgres_password: str = os.environ.get("POSTGRES_PASSWORD", "postgres_password")

    # Embedding configuration
    embedding_model: str = os.environ.get("EMBEDDING_MODEL", "text-embedding-3-small")
    embedding_batch_size: int = int(os.environ.get("EMBEDDING_BATCH_SIZE", "20"))
    # openai.OpenAI will automatically read OPENAI_API_KEY env, we can omitted it.
    # openai_api_key: str = os.environ["OPENAI_API_KEY"]

    # Indexer configuration
    indexer_cron_schedule: str = os.environ.get("INDEXER_CRON_SCHEDULE", "0 * * * *")


settings = Settings()
