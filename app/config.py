from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    supabase_url: str = ""
    supabase_service_role_key: str = ""
    gemini_api_key: str = ""
    embedding_model: str = "models/gemini-embedding-001"
    embedding_dimensions: int = 3072
    generation_model: str = "gemini-3.8-flash"
    http_timeout_seconds: float = 20.0
    max_retries: int = 3
    max_content_bytes: int = 5_000_000
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
