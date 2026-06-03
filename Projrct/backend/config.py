from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/resume_ai"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    use_openai_profile_extraction: bool = False
    use_openai_resume_rewrite: bool = False
    embedding_model: str = "all-MiniLM-L6-v2"
    upload_max_mb: int = 5
    exports_dir: str = "exports"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
