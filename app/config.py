"""
Единая точка загрузки конфигурации приложения.

* Поддерживает три окружения: dev / prod / test.
* Определяет, какой .env-файл подключить, глядя на переменную ENVIRONMENT,
  которую выставляют Docker-compose или CI.
* Никаких динамических «копирований dict» — всё задаётся
  в `model_config` класса Settings раз и навсегда.
"""

from __future__ import annotations

import os
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# ────────────────────────────────────────────────────────────────
# Определяем, какой .env-файл брать
# ────────────────────────────────────────────────────────────────
# ENVIRONMENT обязан быть задан: docker-compose передаёт его из .env
ENVIRONMENT = os.getenv("ENVIRONMENT", "dev").lower()  # dev / prod / test
ENV_FILE = Path(__file__).resolve().parent.parent / f".env.{ENVIRONMENT}"

# Если файла нет, падаем с внятной ошибкой ещё на этапе импорта.
if not ENV_FILE.exists():
    raise FileNotFoundError(
        f"[config] .env-файл для окружения '{ENVIRONMENT}' не найден: {ENV_FILE}"
    )

# ────────────────────────────────────────────────────────────────
# Модель настроек
# ────────────────────────────────────────────────────────────────
class Settings(BaseSettings):
    """Все переменные среды, доступные приложению."""

    # где и как читать переменные
    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",  # лишние переменные не валят приложение
    )

    # базовые
    ENVIRONMENT: str = Field(..., env="ENVIRONMENT")

    # БД / кеш
    DATABASE_URL: str = Field(..., env="DATABASE_URL")
    CELERY_BROKER_URL: str = Field(..., env="CELERY_BROKER_URL")
    CELERY_RESULT_BACKEND: str = Field(..., env="CELERY_RESULT_BACKEND")

    # LLM / Google
    LLM_PROVIDER: str = Field("stub", env="LLM_PROVIDER")            # gemini / stub
    GEMINI_API_KEY: str = Field("", env="GEMINI_API_KEY")
    GOOGLE_PROJECT: str = Field("", env="GOOGLE_PROJECT")

    # Календарь, TTS/STT
    CALENDAR_PROVIDER: str = Field("noop", env="CALENDAR_PROVIDER")  # google / noop
    GOOGLE_CALENDAR_CREDENTIALS_JSON: Path | None = Field(
        None, env="GOOGLE_CALENDAR_CREDENTIALS_JSON"
    )
    SPEECH_LANGUAGE: str = Field("ru-RU", env="SPEECH_LANGUAGE")
    TTS_VOICE: str = Field("ru-RU-Wavenet-D", env="TTS_VOICE")

    # Добавляйте новые поля ниже ⤵︎
    # ...

    # convenience
    @property
    def is_prod(self) -> bool:  # pragma: no cover
        return self.ENVIRONMENT == "prod"


# ────────────────────────────────────────────────────────────────
# Синглтон конфигурации
# ────────────────────────────────────────────────────────────────
settings = Settings()

# ────────────────────────────────────────────────────────────────
# Быстрый локальный самотест (python -m app.config)
# ────────────────────────────────────────────────────────────────
if __name__ == "__main__":  # pragma: no cover
    import json

    print(f"Loaded env file: {ENV_FILE}")
    print(json.dumps(settings.model_dump(mode="json"), indent=2, ensure_ascii=False))
