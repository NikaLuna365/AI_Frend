# app/config.py

"""
Application configuration.

Reads environment variables and `.env.{environment}` file using Pydantic v2 BaseSettings.
Supports three modes via ENVIRONMENT:
  - prod → loads `.env.prod`
  - dev  → loads `.env.dev`
  - test → loads `.env.test`
"""

import os
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Determine which .env file to load based on ENVIRONMENT
env_name = os.getenv("ENVIRONMENT", "dev")
env_file = f".env.{env_name}"

class Settings(BaseSettings):
    # Pydantic v2 settings configuration
    model_config = SettingsConfigDict(
        env_file=env_file,
        env_file_encoding="utf-8",
    )

    # Application environment: prod, dev, or test
    ENVIRONMENT: str = Field(..., env="ENVIRONMENT")

    # Database
    DATABASE_URL: str = Field(..., env="DATABASE_URL")

    # Google Calendar
    GOOGLE_PROJECT: str = Field(..., env="GOOGLE_PROJECT")
    GOOGLE_CALENDAR_CREDENTIALS_JSON: str = Field(..., env="GOOGLE_CALENDAR_CREDENTIALS_JSON")

    # LLM
    GEMINI_API_KEY: str = Field(..., env="GEMINI_API_KEY")
    LLM_PROVIDER: str = Field(..., env="LLM_PROVIDER")

    # Calendar provider
    CALENDAR_PROVIDER: str = Field(..., env="CALENDAR_PROVIDER")

    # Speech / TTS
    SPEECH_LANGUAGE: str = Field(..., env="SPEECH_LANGUAGE")
    TTS_VOICE: str = Field(..., env="TTS_VOICE")

    # Celery
    CELERY_BROKER_URL: str = Field(..., env="CELERY_BROKER_URL")
    CELERY_RESULT_BACKEND: str = Field(..., env="CELERY_RESULT_BACKEND")


# Single global settings instance
settings = Settings()
