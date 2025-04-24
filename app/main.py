import logging

from fastapi import FastAPI
from app.config import settings
from app.api.v1.chat import router as chat_router
from app.api.v1.achievements import router as achievements_router
from app.api.v1.calendar import router as calendar_router
from app.api.v1.audio import router as audio_router

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AI-Drug",
    version=settings.APP_VERSION,
    description="Модуль AI-друга: чат, календарь, достижения и голосовые сообщения"
)

# Включение маршрутов API
app.include_router(chat_router, prefix="/v1/chat", tags=["chat"])
app.include_router(achievements_router, prefix="/v1/achievements", tags=["achievements"])
app.include_router(calendar_router, prefix="/v1/calendar", tags=["calendar"])
app.include_router(audio_router, prefix="/v1/chat_audio", tags=["audio"])

@app.get("/healthz")
def healthz():
    """Проверка доступности сервиса"""
    logger.info("Health check requested")
    return {"status": "ok", "version": settings.APP_VERSION}
