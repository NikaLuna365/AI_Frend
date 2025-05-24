# /app/main.py (Добавляем роутер ачивок)

from __future__ import annotations
import logging
from fastapi import FastAPI, status

# --- Импорты Роутеров ---
from app.api.v1.auth import router as auth_router
from app.api.v1.chat import router as chat_router
# from app.api.v1.calendar import router as cal_router # Отложен для MVP
# from app.api.v1.audio import router as audio_router # Отложен для MVP
from app.api.v1.health import router as health_router
from app.api.v1.achievements_api import router as achievements_router # <--- НОВЫЙ ИМПОРТ
# ------------------------
from app.config import settings

logging.basicConfig(...) # Оставляем как есть
description = """...""" # Оставляем как есть
tags_metadata = [ # Добавляем тег для ачивок
    {"name": "Authentication & Testing", "description": "..."},
    {"name": "chat", "description": "..."},
    {"name": "Achievements", "description": "Operations related to user achievements."}, # <--- НОВЫЙ ТЕГ
    {"name": "Health", "description": "..."},
]

app = FastAPI(...) # Оставляем как есть

# --- Подключение Роутеров ---
app.include_router(auth_router)
app.include_router(chat_router)
# app.include_router(cal_router)
# app.include_router(audio_router)
app.include_router(health_router)
app.include_router(achievements_router) # <--- ПОДКЛЮЧАЕМ НОВЫЙ РОУТЕР
# ---------------------------

logging.getLogger(__name__).info(...) # Оставляем как есть

@app.get("/healthz", ...) # Оставляем как есть
async def health_check():
    return {"status": "ok"}
