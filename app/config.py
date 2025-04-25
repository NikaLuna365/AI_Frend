"""
app.config
~~~~~~~~~~

Единая точка входа для всех настроек приложения.

* Читает .env-файл, выбранный переменной ENVIRONMENT.
* Не использует os.getenv напрямую — всё идёт через Pydantic 2 и
  pydantic-settings.
* Экспортирует готовый объект `settings`, который импортируется
  где угодно: `from app.config import settings`.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# ────────────────────────────────────────────────────────────────
# Карта окружений  →  какой .env подключаем
# ────────────────────────────────────────────────────────────────
_ENV_FILES = {
    "prod": ".env.prod",
    "dev": ".env.dev",
    "test": ".env.test",
}

PROJECT_ROOT = Path(__file__).resolve().parent.parent  # /app
DEFAULT_ENV_FILE = PROJECT_ROOT / ".env"               # fallback


class Settings(BaseSettings):
    """
    Все переменные среды приложения.

    * Поле `model_config` заменяет класс Config из Pydantic 1.x.
    * Значения читаются из .env-файла + системных переменных.
    """

    # ------------------------------------------------------------------
    # где искать .env
    # ------------------------------------------------------------------
    model_config = SettingsConfigDict(
        env_file=DEFAULT_ENV_FILE,      # переопределим ниже в __init__
        env_file_encoding="utf-8",
        extra="ignore",                 # игнорируем неожиданные переменные
    )

    # ------------------------------------------------------------------
    # базовые
    # ------------------------------------------------------------------
    ENVIRONMENT: str = Field("dev", env="ENVIRONMENT")  # dev / prod / test

    # ------------------------------------------------------------------
    # БД и кеши
    # ------------------------------------------------------------------
    DATABASE_URL: str = Field(..., env="DATABASE_URL")
    CELERY_BROKER_URL: str = Field(..., env="CELERY_BROKER_URL")
    CELERY_RESULT_BACKEND: str = Field(..., env="CELERY_RESULT_BACKEND")

    # ------------------------------------------------------------------
    # Google / LLM
    # ------------------------------------------------------------------
    GOOGLE_PROJECT: str = Field(..., env="GOOGLE_PROJECT")
    GEMINI_API_KEY: str = Field(..., env="GEMINI_API_KEY")
    LLM_PROVIDER: str = Field("stub", env="LLM_PROVIDER")  # gemini / stub

    # ------------------------------------------------------------------
    # Календарь / TTS / STT
    # ------------------------------------------------------------------
    CALENDAR_PROVIDER: str = Field("noop", env="CALENDAR_PROVIDER")  # google / noop
    SPEECH_LANGUAGE: str = Field("ru-RU", env="SPEECH_LANGUAGE")
    TTS_VOICE: str = Field("ru-RU-Wavenet-D", env="TTS_VOICE")

    # ------------------------------------------------------------------
    # прочее (добавляйте по мере необходимости)
    # ------------------------------------------------------------------
    # ...

    # ——————————————————————————————————————————————————————————————
    # динамически подменяем env_file в зависимости от ENVIRONMENT
    # ——————————————————————————————————————————————————————————————
    def __init__(self, **data):
        env = data.get("ENVIRONMENT") or (DEFAULT_ENV_FILE.exists() and DEFAULT_ENV_FILE.read_text().split("=", 1)[-1].strip())  # noqa: E501
        env_file_path = PROJECT_ROOT / _ENV_FILES.get(env, ".env")
        object.__setattr__(self, "model_config", self.model_config.copy(update={"env_file": env_file_path}))
        super().__init__(**data)


# Экспортируем singleton
settings = Settings()

# ────────────────────────────────────────────────────────────────
# Быстрый самотест — выводим важные параметры при прямом запуске
# ────────────────────────────────────────────────────────────────
if __name__ == "__main__":  # pragma: no cover
    import json
    print(json.dumps(settings.model_dump(mode="json"), indent=2, ensure_ascii=False))
