# /app/app/config.py (Версия из ответа #63)

from __future__ import annotations

import os
import logging
from pathlib import Path
# Убедимся, что Optional импортирован
from typing import List, Optional, Any, Dict

from pydantic import Field, AnyHttpUrl, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

log = logging.getLogger(__name__)

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # env_file НЕ указан здесь
        case_sensitive=False,
        extra="ignore",
    )

    ENVIRONMENT: str = Field("dev", env="ENVIRONMENT")
    DATABASE_URL: str = Field(..., env="DATABASE_URL")
    REDIS_URL: str = Field("redis://redis:6379/0", env="REDIS_URL")
    CELERY_BROKER_URL: Optional[str] = Field(None, env="CELERY_BROKER_URL")
    CELERY_RESULT_BACKEND: Optional[str] = Field(None, env="CELERY_RESULT_BACKEND")
    JWT_SECRET_KEY: str = Field(..., env="JWT_SECRET_KEY")
    JWT_ALGORITHM: str = Field("HS256", env="JWT_ALGORITHM")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(60 * 24 * 7, env="JWT_ACCESS_TOKEN_EXPIRE_MINUTES")
    LLM_PROVIDER: str = Field("stub", env="LLM_PROVIDER")
    GEMINI_API_KEY: Optional[str] = Field(None, env="GEMINI_API_KEY")
    CALENDAR_PROVIDER: str = Field("noop", env="CALENDAR_PROVIDER")
    # GOOGLE_CLIENT_ID: Optional[str] = Field(None, env="GOOGLE_CLIENT_ID") # Закомментировано для MVP
    # TOKENS_ENCRYPTION_KEY: Optional[str] = Field(None, env="TOKENS_ENCRYPTION_KEY") # Закомментировано для MVP

    @model_validator(mode='after')
    def set_celery_defaults(self) -> 'Settings':
        if self.CELERY_BROKER_URL is None:
            self.CELERY_BROKER_URL = self.REDIS_URL
        if self.CELERY_RESULT_BACKEND is None:
            self.CELERY_RESULT_BACKEND = self.REDIS_URL
        if self.CELERY_BROKER_URL is None or self.CELERY_RESULT_BACKEND is None:
             raise ValueError("Redis URL must be set for Celery defaults") # pragma: no cover
        return self

# --- ЯВНЫЙ ВЫЗОВ model_rebuild ---
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
    log.debug("Loaded settings: DB URL=%s..., Redis URL=%s, LLM Provider=%s",
             str(settings.DATABASE_URL)[:25] if settings.DATABASE_URL else "None",
             settings.REDIS_URL,
             settings.LLM_PROVIDER)
except Exception as e:
    log.exception("Failed to instantiate Settings.")
    raise e
