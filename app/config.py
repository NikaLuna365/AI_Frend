# app/config.py
from __future__ import annotations

import os
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# ────────────────────────────────────────────────────────────────────────────
env_name = os.getenv("ENVIRONMENT", "dev")
env_file = Path(__file__).resolve().parent.parent.parent / f".env.{env_name}"
if not env_file.exists():
    env_file = Path(__file__).resolve().parent.parent.parent / ".env"
# ────────────────────────────────────────────────────────────────────────────


class Settings(BaseSettings):
    """Единый конфиг проекта (Pydantic 2 + pydantic-settings)."""

    model_config = SettingsConfigDict(
        env_file=str(env_file),
        env_file_encoding="utf-8",
        extra="forbid",           # лишние переменные → ошибка
    )

    # basic
    ENVIRONMENT: str = Field(..., env="ENVIRONMENT")

    # database
    DATABASE_URL: str = Field(..., env="DATABASE_URL")

    # redis / celery
    redis_url: str = Field("redis://redis:6379/0", env="REDIS_URL")          # <-- NEW
    celery_broker_url: str = Field("redis://redis:6379/0", env="CELERY_BROKER_URL")
    celery_result_backend: str = Field("redis://redis:6379/0", env="CELERY_RESULT_BACKEND")

    # providers
    LLM_PROVIDER: str = Field("stub", env="LLM_PROVIDER")
    CALENDAR_PROVIDER: str = Field("noop", env="CALENDAR_PROVIDER")


settings = Settings()
