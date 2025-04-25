# app/config.py
"""
Единая точка загрузки настроек из .env.{env_name}

• ENVIRONMENT   – prod / dev / test   (по умолчанию dev)
• Все остальные переменные описаны в классе Settings.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ------------------------------------------------------------------ #
    # базовые
    # ------------------------------------------------------------------ #
    ENVIRONMENT: str = Field("dev", description="dev / prod / test")
    APP_VERSION: str = "0.2.0"

    # ------------------------------------------------------------------ #
    # База данных и Redis
    # ------------------------------------------------------------------ #
    DATABASE_URL: str = Field(..., description="postgresql://user:pass@host/db  ИЛИ  sqlite:///file.db")
    REDIS_URL: str = Field("redis://redis:6379/0")

    # ------------------------------------------------------------------ #
    # Google, LLM, Календарь
    # ------------------------------------------------------------------ #
    GEMINI_API_KEY: str | None = None
    GOOGLE_CALENDAR_CREDENTIALS_JSON: str | None = None
    LLM_PROVIDER: str = "gemini"          # gemini / stub
    CALENDAR_PROVIDER: str = "google"     # google / noop

    # ------------------------------------------------------------------ #
    # Speech / TTS
    # ------------------------------------------------------------------ #
    SPEECH_LANGUAGE: str = "ru-RU"
    TTS_VOICE: str = "ru-RU-Wavenet-D"

    # ------------------------------------------------------------------ #
    # Celery
    # ------------------------------------------------------------------ #
    CELERY_BROKER_URL: str = Field(default_factory=lambda: os.getenv("REDIS_URL", "redis://redis:6379/0"))
    CELERY_RESULT_BACKEND: str = Field(default_factory=lambda: os.getenv("REDIS_URL", "redis://redis:6379/0"))

    # ------------------------------------------------------------------ #
    # pydantic-settings meta
    # ------------------------------------------------------------------ #
    model_config = SettingsConfigDict(env_file=None, case_sensitive=False)


@lru_cache
def get_settings() -> Settings:
    """лениво читаем .env.<ENVIRONMENT>"""
    env_name = os.getenv("ENVIRONMENT", "dev")
    dotenv_path = Path(__file__).resolve().parent.parent / f".env.{env_name}"
    if dotenv_path.exists():
        # pydantic-settings ищет env-файл, если передан через Environment variables
        os.environ.setdefault("Pydantic_Settings__env_file", str(dotenv_path))
    return Settings()  # type: ignore[arg-type]


settings: Settings = get_settings()
