from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    ENVIRONMENT: Literal["prod", "dev", "test"] = Field("dev", env="ENVIRONMENT")

    # DB / Cache
    DATABASE_URL: str = "sqlite:///./app.db"
    CELERY_BROKER_URL: str = "redis://redis:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/0"

    # Providers
    LLM_PROVIDER: str = "stub"  # stub | gemini
    CALENDAR_PROVIDER: str = "noop"  # noop | google

    # Google creds
    GOOGLE_CALENDAR_CREDENTIALS_JSON: str = "./credentials/calendar.json"
    GEMINI_API_KEY: str | None = None

    class Config:
        env_file = f".env.{os.getenv('ENVIRONMENT', 'dev')}"
        env_file_encoding = "utf-8"


@lru_cache
def _cached() -> Settings:
    return Settings()  # type: ignore[call-arg]


settings = _cached()  # все импорты тянут один экземпляр
