# /app/app/config.py (Исправленная версия v3)

from __future__ import annotations

import os
import logging # Добавляем logging
from pathlib import Path
# --- ВАЖНО: Убедимся, что Optional импортирован из typing ПЕРЕД использованием ---
from typing import List, Optional, Any, Dict # Добавляем Any, Dict

# --- Импорты Pydantic ---
from pydantic import Field, AnyHttpUrl, model_validator # Убираем validator, используем model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

log = logging.getLogger(__name__)

# --- Логика определения пути к .env файлу (для информации, но не для pydantic-settings) ---
# env_name = os.getenv("ENVIRONMENT", "dev")
# _project_dir = Path(__file__).resolve().parent.parent.parent
# env_file_to_log = _project_dir / f".env.{env_name}"
# if not env_file_to_log.exists():
#     env_file_to_log = _project_dir / ".env"
# log.info(f"Attempting to load settings. Expected .env file (for docker-compose): {env_file_to_log}")
# ------------------------------------------------------------------------------------

class Settings(BaseSettings):
    """
    Единый конфиг проекта. Читает переменные окружения.
    Pydantic v2 + pydantic-settings.
    """
    # --- Конфигурация Pydantic Settings ---
    model_config = SettingsConfigDict(
        # --- УБИРАЕМ env_file отсюда ---
        # Pydantic-settings будет читать ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ,
        # которые Docker Compose установит из файла, указанного в docker-compose.yml.
        # env_file=_env_file_path_str,
        # env_file_encoding="utf-8",
        # --------------------------------
        case_sensitive=False, # Имена переменных окружения не чувствительны к регистру
        extra="ignore", # Игнорировать лишние переменные окружения
    )

    # --- Основные настройки ---
    # Используем Optional и None как дефолт, если переменная может отсутствовать
    # Docker Compose должен передать ENVIRONMENT=dev (или prod/test)
    ENVIRONMENT: str = Field("dev", description="Application environment (dev, test, prod)")

    # --- База данных ---
    # DATABASE_URL обязателен, поэтому нет Optional и нет дефолта
    DATABASE_URL: str = Field(..., description="Async database connection URL (e.g., postgresql+asyncpg://...)" )

    # --- Redis / Celery ---
    REDIS_URL: str = Field("redis://redis:6379/0", description="URL for Redis connection")
    # Оставляем возможность задать их отдельно, но по умолчанию берем из REDIS_URL через валидатор
    CELERY_BROKER_URL: Optional[str] = Field(None, description="Celery broker URL (defaults to REDIS_URL)")
    CELERY_RESULT_BACKEND: Optional[str] = Field(None, description="Celery result backend URL (defaults to REDIS_URL)")

    # --- JWT Настройки ---
    JWT_SECRET_KEY: str = Field(..., description="Secret key for signing JWT tokens") # Обязателен
    JWT_ALGORITHM: str = Field("HS256", description="Algorithm for JWT signing")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(60 * 24 * 7, description="JWT access token lifetime in minutes") # 7 дней

    # --- Настройки Провайдеров ---
    # LLM
    LLM_PROVIDER: str = Field("stub", description="LLM provider to use ('stub', 'gemini')")
    GEMINI_API_KEY: Optional[str] = Field(None, description="API Key for Google Gemini")

    # Calendar (Отложено для MVP)
    CALENDAR_PROVIDER: str = Field("noop", description="Calendar provider ('noop', 'google')")
    # GOOGLE_PROJECT: Optional[str] = None
    # GOOGLE_CALENDAR_CREDENTIALS_JSON: Optional[str] = None

    # Google Auth (Отложено, но поле можно оставить)
    # GOOGLE_CLIENT_ID: Optional[str] = None

    # Ключ шифрования токенов (Отложено)
    # TOKENS_ENCRYPTION_KEY: Optional[str] = None

    # --- Динамические значения по умолчанию для Celery ---
    @model_validator(mode='after')
    def set_celery_defaults(self) -> 'Settings':
        if self.CELERY_BROKER_URL is None:
            log.debug("Setting CELERY_BROKER_URL default from REDIS_URL")
            self.CELERY_BROKER_URL = self.REDIS_URL
        if self.CELERY_RESULT_BACKEND is None:
            log.debug("Setting CELERY_RESULT_BACKEND default from REDIS_URL")
            self.CELERY_RESULT_BACKEND = self.REDIS_URL
        # Проверим, что они не остались None после валидации
        if self.CELERY_BROKER_URL is None or self.CELERY_RESULT_BACKEND is None:
             raise ValueError("Redis URL must be set for Celery defaults") # pragma: no cover
        return self

# --- ЯВНЫЙ ВЫЗОВ model_rebuild ---
# Вызываем после определения класса, но перед созданием экземпляра
# Это помогает Pydantic разрешить все типы и зависимости.
try:
    Settings.model_rebuild(force=True)
    log.debug("Pydantic Settings model rebuilt successfully.")
except Exception as e:
    log.exception("Failed to rebuild Pydantic Settings model.")
    raise e
# --------------------------------

# --- Создание единственного экземпляра настроек ---
try:
    settings = Settings()
    log.info("Settings loaded successfully for ENVIRONMENT=%s", settings.ENVIRONMENT)
    # Опционально: Можно залоггировать часть настроек для проверки (БЕЗ СЕКРЕТОВ!)
    log.debug("Loaded settings: DB URL=%s..., Redis URL=%s, LLM Provider=%s",
             str(settings.DATABASE_URL)[:25] if settings.DATABASE_URL else "None",
             settings.REDIS_URL,
             settings.LLM_PROVIDER)
except Exception as e:
    log.exception("Failed to instantiate Settings.")
    # Если не удалось создать настройки, приложение не сможет работать
    raise e
