"""Configuration management for the agent service."""

import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    # Database configuration
    postgres_host: str = os.environ["POSTGRES_HOST"]
    postgres_port: int = int(os.environ["POSTGRES_PORT"])
    postgres_db: str = os.environ["POSTGRES_DB"]
    postgres_user: str = os.environ["POSTGRES_USER"]
    postgres_password: str = os.environ["POSTGRES_PASSWORD"]

    # langchan_openai.ChatOpenAI will automatically read OPENAI_API_KEY env, we can omitted it.
    # openai_api_key: str = os.environ["OPENAI_API_KEY"]

    # Embedding configuration
    embedding_model: str = os.environ["EMBEDDING_MODEL"]

    # Chat models configuration
    fast_model: str = os.environ["FAST_MODEL"]
    generation_model: str = os.environ["GENERATION_MODEL"]

    # Vector search configuration
    match_threshold: float = float(os.environ.get("MATCH_THRESHOLD", "0.35"))


settings = Settings()
