# app/config.py

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    """

    # Application
    APP_VERSION: str = Field("0.1.0", description="Application version")
    ENVIRONMENT: str = Field("development", description="Environment (development, production, etc.)")

    # Database
    DATABASE_URL: str = Field(..., description="PostgreSQL connection URL, e.g. postgresql://user:pass@host:port/dbname")

    # Google Calendar
    GOOGLE_PROJECT: str = Field(..., description="Google Cloud project ID")
    GOOGLE_CALENDAR_CREDENTIALS_JSON: str = Field(
        ..., description="Path to service account JSON file for Google Calendar API"
    )

    # Gemini LLM
    GEMINI_API_KEY: str = Field(..., description="API key for Google Gemini")
    LLM_PROVIDER: str = Field("gemini", description="LLM provider to use (e.g. 'gemini')")

    # Calendar provider
    CALENDAR_PROVIDER: str = Field("google", description="Calendar provider to use (e.g. 'google')")

    # Speech-to-Text / Text-to-Speech
    SPEECH_LANGUAGE: str = Field("ru-RU", description="Language code for speech recognition")
    TTS_VOICE: str = Field("ru-RU-Wavenet-D", description="Voice name for text-to-speech synthesis")

    # Celery configuration
    CELERY_BROKER_URL: str = Field(..., description="URL of Celery broker (e.g. redis://redis:6379/0)")
    CELERY_RESULT_BACKEND: str = Field(..., description="URL of Celery result backend (e.g. redis://redis:6379/0)")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Instantiate the settings object for import across the application
settings = Settings()
