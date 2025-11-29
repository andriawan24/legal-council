from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Extraction model settings
    extraction_model: str = "gemini-2.5-flash-lite"
    extraction_fallback_model: str = "gemini-2.5-flash"
    extraction_fallback_model_2: str = "gemini-2.5-pro"
    extraction_chunk_size: int = 10
    async_http_request_timeout: int = 60

    # Embedding settings
    # gemini-embedding-001: up to 3072 dims, 2048 tokens, excellent multilingual
    embedding_model: str = "gemini-embedding-001"
    embedding_dimension: int = 3072  # Full Gemini precision
    embedding_batch_size: int = 250
    embedding_max_text_length: int = 8000  # ~2048 tokens max
    embedding_chunk_overlap: int = 500
    enable_embeddings: bool = True
    enable_chunk_embeddings: bool = False

    # GCP Project settings (usually from env)
    gcp_project: str = "google-marathon"
    gcp_region: str = "us-central1"

    # Database settings (Cloud SQL with pgvector)
    database_url: str | None = None
    database_pool_min_size: int = 1
    database_pool_max_size: int = 10
    database_command_timeout: int = 60
    enable_database_storage: bool = True

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()
