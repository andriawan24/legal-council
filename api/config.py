"""
Configuration settings for the Legal Council API.

Uses pydantic-settings for environment variable management.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """API configuration settings."""

    # API Settings
    api_title: str = "Legal Council API"
    api_version: str = "1.0.0"
    api_prefix: str = "/api/v1"
    debug: bool = False

    # CORS Settings
    cors_origins: list[str] = ["*"]

    # Database Settings (Cloud SQL with pgvector)
    database_url: str | None = None
    database_pool_min_size: int = 1
    database_pool_max_size: int = 10
    database_command_timeout: int = 60

    # GCP Settings
    gcp_project: str = "cloud-run-marathon"
    gcp_region: str = "asia-southeast2"  # Jakarta region for Cloud Run deployment

    # Vertex AI Settings
    vertex_ai_model: str = "gemini-2.5-flash"
    # text-embedding-004: 768 dims, works with TextEmbeddingModel API in us-central1
    vertex_ai_embedding_model: str = "text-embedding-004"
    embedding_dimension: int = 768  # Native dimension, pgvector compatible

    # Rate Limiting
    rate_limit_requests: int = 100
    rate_limit_window_seconds: int = 60

    # Session Settings
    session_max_messages: int = 100
    session_timeout_hours: int = 24

    # Vector Search Settings
    vector_search_limit: int = 10
    vector_search_min_similarity: float = 0.5

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
