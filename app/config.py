from pydantic import BaseSettings, Field

class Settings(BaseSettings):
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: str = Field("development", env="ENVIRONMENT")

    # Database
    DATABASE_URL: str = Field(..., env="DATABASE_URL")

    # Google API
    GOOGLE_PROJECT: str = Field(..., env="GOOGLE_PROJECT")
    GOOGLE_CALENDAR_CREDENTIALS_JSON: str = Field(..., env="GOOGLE_CALENDAR_CREDENTIALS_JSON")

    # Gemini
    GEMINI_API_KEY: str = Field(..., env="GEMINI_API_KEY")
    LLM_PROVIDER: str = Field("gemini", env="LLM_PROVIDER")
    CALENDAR_PROVIDER: str = Field("google", env="CALENDAR_PROVIDER")

    # Speech
    SPEECH_LANGUAGE: str = Field("ru-RU", env="SPEECH_LANGUAGE")
    TTS_VOICE: str = Field("ru-RU-Wavenet-D", env="TTS_VOICE")

    # Celery
    CELERY_BROKER_URL: str = Field(..., env="CELERY_BROKER_URL")
    CELERY_RESULT_BACKEND: str = Field(..., env="CELERY_RESULT_BACKEND")

    class Config:
        env_file = ".env"

settings = Settings()
