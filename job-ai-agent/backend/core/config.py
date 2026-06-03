from functools import lru_cache
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AI Job Hunter"
    environment: str = "development"
    log_level: str = "INFO"

    database_url: str = Field(
        default="postgresql+psycopg://jobhunter:jobhunter@localhost:5432/jobhunter"
    )
    api_cors_origins: List[str] = Field(default_factory=lambda: ["*"])

    openai_api_key: str | None = None
    openrouter_api_key: str | None = None

    linkedin_headless: bool = True
    collector_min_delay_seconds: float = 2.5
    collector_max_delay_seconds: float = 7.0
    collector_max_pages: int = 2

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @field_validator("api_cors_origins", mode="before")
    @classmethod
    def split_cors_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()

