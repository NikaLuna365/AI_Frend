"""
app/config.py
~~~~~~~~~~~~~
Единая точка входа для всех настроек приложения.

* никаких прямых os.getenv() в коде;
* поддержка трёх окружений: prod / dev / test;
* подхватывает .env.<ENVIRONMENT> автоматически;
* экспортирует объект `settings`, который и импортируется далее.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import BaseSettings, Field, PostgresDsn, RedisDsn, validator

# ────────────────────────────────────────────────────────────
# базовые пути
# ────────────────────────────────────────────────────────────
ROOT_DIR = Path(__file__).resolve().parents[1]          # …/app
ENV_DIR = ROOT_DIR.parent                               # корень репо


class _Base(BaseSettings):
    """Параметры, общие для всех окружений."""

    # режим работы — используется и в коде, и в логах
    ENVIRONMENT: Literal["prod", "dev", "test"] = Field(
        default="prod",
        description="prod | dev | test  — определяет набор .env-файла и спец-режимы",
    )

    # База данных
    DATABASE_URL: PostgresDsn = Field(
        default="postgresql://user:password@db:5432/ai_friend",
        description="DSN Postgres",
    )

    # Redis / Celery
    CELERY_BROKER_URL: RedisDsn = "redis://redis:6379/0"
    CELERY_RESULT_BACKEND: RedisDsn = "redis://redis:6379/1"

    # LLM & Calendar
    LLM_PROVIDER: Literal["gemini", "stub"] = "stub"
    CALENDAR_PROVIDER: Literal["google", "noop"] = "noop"

    GEMINI_API_KEY: str | None = None  # для prod

    GOOGLE_CALENDAR_CREDENTIALS_JSON: Path | None = None

    # Прочее
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    SPEECH_LANGUAGE: str = "ru-RU"
    TTS_VOICE: str = "ru-RU-Wavenet-D"

    class Config:
        env_file = ".env"  # будет переопределено ниже
        case_sensitive = True

    # ────────────────────────────────────────────────────────
    # дополнительные валидаторы/расчёты
    # ────────────────────────────────────────────────────────
    @validator("GOOGLE_CALENDAR_CREDENTIALS_JSON", pre=True)
    def _validate_path(cls, v: str | Path | None) -> Path | None:
        if v is None:
            return None
        return Path(v).expanduser().resolve()


# ────────────────────────────────────────────────────────────
# фабрика-обёртка, чтобы lazily подгружать env-файл
# ────────────────────────────────────────────────────────────
@lru_cache()
def _build_settings() -> _Base:
    env = os.getenv("ENVIRONMENT", "prod").lower()

    # .env.prod / .env.dev / .env.test
    env_file = ENV_DIR / f".env.{env}"
    if env_file.exists():
        _Base.Config.env_file = env_file  # type: ignore[attr-defined]
    else:
        # fallback на обычный .env
        _Base.Config.env_file = ENV_DIR / ".env"  # type: ignore[attr-defined]

    s = _Base()  # type: ignore[call-arg]
    # в тестах включаем Celery eager-mode
    if env == "test":
        s.CELERY_TASK_ALWAYS_EAGER = True  # type: ignore[attr-defined]

    return s


# Экспортируем единый экземпляр
settings: _Base = _build_settings()
