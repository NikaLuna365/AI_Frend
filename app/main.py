# app/main.py

from __future__ import annotations

import logging

# --- ИСПРАВЛЕНИЕ: Добавляем импорт status ---
from fastapi import FastAPI, status # <--- Добавили status
# ----------------------------------------
# --- Остальные импорты ---
from app.api.v1.auth import router as auth_router
from app.api.v1.chat import router as chat_router
from app.api.v1.calendar import router as cal_router
from app.api.v1.audio import router as audio_router
from app.api.v1.health import router as health_router
from app.config import settings
# from .exceptions import add_exception_handlers # Закомментировано

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

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
    {"name": "Authentication", "description": "Operations related to user authentication and authorization."},
    {"name": "chat", "description": "Endpoints for interacting with the AI chat."},
    {"name": "Health", "description": "API Health Checks"}, # Добавим тег для health
    # Добавьте другие теги по мере необходимости
]

app = FastAPI(
    title="AI-Friend API",
    description=description,
    version="0.2.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=tags_metadata
)

# Подключаем роутеры
app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(cal_router)
app.include_router(audio_router)
# --- Проверяем, подключен ли health_router ---
# Если health_router уже реализует /healthz, то эндпоинт ниже не нужен.
# Если нет, то эндпоинт ниже его реализует.
# Предположим, health_router существует, но может не иметь /healthz
# app.include_router(health_router) # Если /healthz в нем, раскомментировать и удалить @app.get ниже

# add_exception_handlers(app) # Закомментировано

logging.getLogger(__name__).info("🌱 FastAPI started in %s mode", settings.ENVIRONMENT)

# --- Health Check эндпоинт ---
# Убедимся, что status теперь импортирован
@app.get("/healthz", tags=["Health"], status_code=status.HTTP_200_OK)
async def health_check():
    """Basic health check endpoint."""
    return {"status": "ok"}
