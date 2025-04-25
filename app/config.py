# app/config.py
from functools import lru_cache
from pathlib import Path
from pydantic import BaseSettings, Field, PostgresDsn, RedisDsn

BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    ENVIRONMENT: str = Field("dev", regex="^(dev|prod|test)$")

    # DB / Cache
    DATABASE_URL: PostgresDsn = "postgresql://ai_user:StrongPass@db:5432/ai_drug"
    REDIS_URL: RedisDsn = "redis://redis:6379/0"

    # Providers
    LLM_PROVIDER: str = "stub"          # gemini | stub
    CALENDAR_PROVIDER: str = "noop"     # google | noop

    # External creds
    GEMINI_API_KEY: str | None = None
    GOOGLE_CALENDAR_CREDENTIALS_JSON: Path | None = None

    class Config:
        env_file = f".env.{BaseSettings().ENVIRONMENT}"
        env_file_encoding = "utf-8"
        case_sensitive = True

@lru_cache
def get_settings() -> Settings:
    return Settings()
