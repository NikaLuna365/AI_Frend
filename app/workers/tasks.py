# /app/app/workers/tasks.py (Проверенная версия БЕЗ задач для MVP)

from __future__ import annotations
import logging

# --- Импорт Celery и настроек ---
from celery import Celery
from app.config import settings # Нужен для URL брокера/бэкенда

log = logging.getLogger(__name__)

# --- ВАЖНО: Определение экземпляра Celery ---
celery_app = Celery(
    "ai-friend", # Имя приложения Celery
    broker=settings.CELERY_BROKER_URL, # URL брокера из config.py
    backend=settings.CELERY_RESULT_BACKEND, # URL бэкенда из config.py
    include=['app.workers.tasks'], # Можно оставить или убрать, если задач нет
    task_serializer='json',
    result_serializer='json',
    accept_content=['json']
)
# --------------------------------------

# --- Конфигурация (опционально) ---
celery_app.conf.update(
    task_track_started=True,
    timezone = 'UTC',
)

# --- Расписание Beat (Закомментировано/Удалено для MVP) ---
# celery_app.conf.beat_schedule = {}

# --- Определения Задач (@celery_app.task) ---
# --- ПОКА ЗАДАЧ НЕТ ДЛЯ MVP ---
# --------------------------------------------

# --- Экспорт для обнаружения Celery ---
__all__ = ["celery_app"]
