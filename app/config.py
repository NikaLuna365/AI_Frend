# /app/app/config.py (Финальная версия с JWT Expiry)

from __future__ import annotations

import os
from pathlib import Path
from typing import List # Добавляем импорт List, если он используется

from pydantic import Field, AnyHttpUrl # Добавляем AnyHttpUrl, если он используется
from pydantic_settings import BaseSettings, SettingsConfigDict

# Определяем окружение и путь к .env файлу
env_name = os.getenv("ENVIRONMENT", "dev")
# Корректный путь к корню проекта (три уровня вверх от config.py)
_project_dir = Path(__file__).resolve().parent.parent.parent
env_file = _project_dir / f".env.{env_name}"
# Фолбэк на .env в корне, если .env.{env_name} не найден
if not env_file.exists():
    env_file = _project_dir / ".env"

# Проверяем существование файла .env (опционально, но полезно для отладки)
if not env_file.exists():
     print(f"Warning: Environment file '{env_file}' not found. Using default settings or env vars.")
     _env_file_path_str = None
else:
     _env_file_path_str = str(env_file)


class Settings(BaseSettings):
    """Единый конфиг проекта (Pydantic 2 + pydantic-settings)."""

    # --- Конфигурация Pydantic Settings ---
    model_config = SettingsConfigDict(
        env_file=_env_file_path_str, # Используем определенный путь
        env_file_encoding="utf-8",
        case_sensitive=False, # Имена переменных окружения не чувствительны к регистру
        extra="ignore", # Игнорировать лишние переменные в .env (вместо 'forbid')
    )

    # --- Основные настройки ---
    ENVIRONMENT: str = Field("dev", env="ENVIRONMENT") # Значение по умолчанию "dev"

    # --- База данных ---
    # URL должен начинаться с postgresql+asyncpg:// для асинхронной работы
    DATABASE_URL: str = Field(..., env="DATABASE_URL")

    # --- Redis / Celery ---
    # Предоставляем значения по умолчанию, если они не заданы в .env
    REDIS_URL: str = Field("redis://redis:6379/0", env="REDIS_URL")
    CELERY_BROKER_URL: str = Field(env="CELERY_BROKER_URL", default="") # Заполняется ниже
    CELERY_RESULT_BACKEND: str = Field(env="CELERY_RESULT_BACKEND", default="") # Заполняется ниже

    # --- JWT Настройки ---
    JWT_SECRET_KEY: str = Field(..., env="JWT_SECRET_KEY") # Секретный ключ обязателен
    JWT_ALGORITHM: str = Field("HS256", env="JWT_ALGORITHM")
    # --- ДОБАВЛЕНО: Время жизни токена ---
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(60 * 24 * 7, env="JWT_ACCESS_TOKEN_EXPIRE_MINUTES") # 7 дней по умолчанию

    # --- Настройки Провайдеров ---
    # LLM
    LLM_PROVIDER: str = Field("stub", env="LLM_PROVIDER") # По умолчанию заглушка
    GEMINI_API_KEY: Optional[str] = Field(None, env="GEMINI_API_KEY") # Ключ опционален

    # Calendar (Отложено для MVP, но поля можно оставить)
    CALENDAR_PROVIDER: str = Field("noop", env="CALENDAR_PROVIDER")
    # GOOGLE_PROJECT: Optional[str] = Field(None, env="GOOGLE_PROJECT")
    # GOOGLE_CALENDAR_CREDENTIALS_JSON: Optional[str] = Field(None, env="GOOGLE_CALENDAR_CREDENTIALS_JSON")

    # Google Auth (только Client ID для верификации ID токена в будущем)
    # GOOGLE_CLIENT_ID: Optional[str] = Field(None, env="GOOGLE_CLIENT_ID")

    # Ключ шифрования токенов (понадобится для Google Calendar)
    # TOKENS_ENCRYPTION_KEY: Optional[str] = Field(None, env="TOKENS_ENCRYPTION_KEY")

    # --- Динамические значения по умолчанию ---
    # Используем @model_validator для установки значений по умолчанию на основе других полей
    # Это более современный подход в Pydantic v2, чем @validator
    from pydantic import model_validator

    @model_validator(mode='after')
    def set_celery_defaults(self) -> 'Settings':
        if not self.CELERY_BROKER_URL:
            self.CELERY_BROKER_URL = self.REDIS_URL
        if not self.CELERY_RESULT_BACKEND:
            self.CELERY_RESULT_BACKEND = self.REDIS_URL
        return self

# --- Создание единственного экземпляра настроек ---
settings = Settings()

# Опционально: Проверка ключа шифрования (если он задан)
# if settings.TOKENS_ENCRYPTION_KEY:
#     try:
#         from cryptography.fernet import Fernet
#         Fernet(settings.TOKENS_ENCRYPTION_KEY.encode())
#     except Exception as e:
#         raise ValueError(f"Invalid TOKENS_ENCRYPTION_KEY: {e}") from e
