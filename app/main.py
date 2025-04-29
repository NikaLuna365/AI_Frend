# app/main.py

from __future__ import annotations

import logging

from fastapi import FastAPI
# --- Добавляем импорт нового роутера ---
from app.api.v1.auth import router as auth_router
# --------------------------------------
from app.api.v1.chat import router as chat_router
from app.api.v1.calendar import router as cal_router
from app.api.v1.audio import router as audio_router
from app.api.v1.health import router as health_router
from app.config import settings
# --- Место для добавления обработчиков исключений ---
# from .exceptions import add_exception_handlers
# --------------------------------------------------

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

# --- Конфигурация описания API (опционально) ---
description = """
AI-Friend API helps you manage your conversations and schedule. 🚀

**Features:**
*   Chat with AI
*   Calendar Integration (soon!)
*   Achievements (soon!)
*   Reminders (soon!)

**Authentication:** Uses JWT tokens obtained via `/v1/auth/login/test` (Dev Only) or Google Sign-In (Later).
"""

tags_metadata = [
    {
        "name": "Authentication",
        "description": "Operations related to user authentication and authorization.",
    },
    {
        "name": "chat",
        "description": "Endpoints for interacting with the AI chat.",
    },
    # Добавьте другие теги по мере необходимости
]
# ------------------------------------------------------


app = FastAPI(
    title="AI-Friend API",
    description=description, # Добавили описание
    version="0.2.0", # Увеличили версию после добавления auth
    docs_url="/docs",
    redoc_url="/redoc", # Добавили ReDoc
    openapi_tags=tags_metadata # Добавили метаданные тегов
)

# Подключаем роутеры
app.include_router(auth_router) # Подключаем роутер аутентификации
app.include_router(chat_router)
app.include_router(cal_router)
app.include_router(audio_router)
app.include_router(health_router)

# --- Место для добавления обработчиков исключений ---
# add_exception_handlers(app)
# --------------------------------------------------


logging.getLogger(__name__).info("🌱 FastAPI started in %s mode", settings.ENVIRONMENT)

# --- Добавляем Health Check эндпоинт, если его нет в health_router ---
# (Проверьте содержимое app/api/v1/health.py)
# Если его там нет, можно добавить простой здесь:
@app.get("/healthz", tags=["Health"], status_code=status.HTTP_200_OK)
async def health_check():
    """Basic health check endpoint."""
    return {"status": "ok"}
# ----------------------------------------------------------------------
