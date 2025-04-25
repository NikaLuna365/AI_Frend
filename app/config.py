"""
Единый конфиг приложения.

•  BaseSettings – через pydantic-settings (PyDantic v2).
•  Три окружения: prod / dev / test.
•  Для test подменяем DATABASE_URL на SQLite in-memory,
   а LLM_PROVIDER – на «stub».
"""

from __future__ import annotations

import os
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


# ─────────────────────────────────────────────────────────────────────────────
#  Utilities
# ─────────────────────────────────────────────────────────────────────────────

BASE_DIR = Path(__file__).resolve().parent.parent
ENVIRONMENT = os.getenv("ENVIRONMENT", "dev").lower()
ENV_FILE = BASE_DIR / f".env.{ENVIRONMENT}"    # .env.dev / .env.test / ...


# ─────────────────────────────────────────────────────────────────────────────
#  Settings
# ─────────────────────────────────────────────────────────────────────────────

class Settings(BaseSettings):
    # Где читать переменные
    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
    )

    # ─────────── Core ───────────
    ENVIRONMENT: str = Field(ENVIRONMENT, env="ENVIRONMENT")

    DATABASE_URL: str = Field(
        default="sqlite:///./local.db",  # перезаписывается в init
        env="DATABASE_URL",
    )

    REDIS_URL: str = Field("redis://redis:6379/0", env="REDIS_URL")
    LLM_PROVIDER: str = Field("stub", env="LLM_PROVIDER")

    # Google / Gemini keys (prod / dev)
    GOOGLE_PROJECT: str | None = Field(None, env="GOOGLE_PROJECT")
    GEMINI_API_KEY: str | None = Field(None, env="GEMINI_API_KEY")

    # ─────────── Dynamic post-init ───────────
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        if self.ENVIRONMENT == "test":
            # Юнит-тесты – SQLite in-memory и заглушки
            object.__setattr__(self, "DATABASE_URL", "sqlite:///:memory:")
            object.__setattr__(self, "LLM_PROVIDER", "stub")


settings = Settings()
