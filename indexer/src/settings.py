"""Configuration management for the indexer service."""

import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings for the indexer service."""

    # Database configuration
    postgres_host: str = os.environ["POSTGRES_HOST"]
    postgres_port: int = int(os.environ["POSTGRES_PORT"])
    postgres_db: str = os.environ["POSTGRES_DB"]
    postgres_user: str = os.environ["POSTGRES_USER"]
    postgres_password: str = os.environ["POSTGRES_PASSWORD"]

    # Embedding configuration
    embedding_model: str = os.environ["EMBEDDING_MODEL"]
    embedding_batch_size: int = int(os.environ["EMBEDDING_BATCH_SIZE"])
    # openai.OpenAI will automatically read OPENAI_API_KEY env, we can omitted it.
    # openai_api_key: str = os.environ["OPENAI_API_KEY"]

    # Indexer configuration
    indexer_cron_schedule: str = os.environ["INDEXER_CRON_SCHEDULE"]


settings = Settings()
