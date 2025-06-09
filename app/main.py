from __future__ import annotations
import logging

from fastapi import FastAPI, status

from app.api.v1.auth import router as auth_router
from app.api.v1.chat import router as chat_router
from app.api.v1.health import router as health_router
from app.api.v1.calendar import router as calendar_router
from app.api.v1.achievements_api import router as achievements_router
from app.api.v1.audio import router as audio_router
from app.config import settings

# Configure basic logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)
description = """...""" # Оставляем как есть
tags_metadata = [ # Добавляем тег для ачивок
    {"name": "Authentication & Testing", "description": "..."},
    {"name": "chat", "description": "..."},
    {"name": "Achievements", "description": "Operations related to user achievements."}, # <--- НОВЫЙ ТЕГ
    {"name": "Health", "description": "..."},
]

app = FastAPI(
    title="AI-Friend API",
    description=description,
    version="0.2.3",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=tags_metadata,
)

app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(health_router)
app.include_router(calendar_router)
app.include_router(achievements_router)
app.include_router(audio_router)

log.info("\U0001F331 FastAPI application configured. Environment: %s", settings.ENVIRONMENT)

@app.on_event("startup")
async def startup_event() -> None:
    log.info("\U0001F680 FastAPI application startup complete.")

@app.on_event("shutdown")
async def shutdown_event() -> None:
    log.info("\U0001F44B FastAPI application shutdown.")

@app.get("/healthz", tags=["Health"], status_code=status.HTTP_200_OK)
async def health_check():
    """Basic health check endpoint."""
    return {"status": "ok", "environment": settings.ENVIRONMENT}
