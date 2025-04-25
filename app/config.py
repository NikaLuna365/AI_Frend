# app/config.py
from __future__ import annotations

import os
from pathlib import Path
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # глобальное
    ENVIRONMENT: str = "dev"                 # dev / prod / test

    # внешние сервисы
    DATABASE_URL: str = "sqlite:///:memory:"
    REDIS_URL: str = "redis://redis:6379/0"

    GEMINI_API_KEY: str | None = None
    GOOGLE_CREDENTIALS_JSON: str | None = None

    # провайдеры
    LLM_PROVIDER: str = "stub"               # gemini / stub
    CALENDAR_PROVIDER: str = "noop"          # google / noop

    # celery
    CELERY_BROKER_URL: str | None = None
    CELERY_RESULT_BACKEND: str | None = None

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def is_test(self) -> bool:       # удобный флаг
        return self.ENVIRONMENT == "test"


def _env_specific_path() -> Path | None:
    env_name = os.getenv("ENVIRONMENT")
    if env_name and Path(f".env.{env_name}").is_file():
        return Path(f".env.{env_name}")
    return None


@lru_cache
def get_settings() -> Settings:
    # если задано .env.<env>, подгружаем поверх
    extra = _env_specific_path()
    if extra:
        os.environ["Pydantic_Extra_Env_File"] = str(extra)
    return Settings()  # type: ignore[arg-type]


settings = get_settings()
