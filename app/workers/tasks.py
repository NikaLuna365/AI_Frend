# /app/app/workers/tasks.py (Упрощенная версия для MVP)
from __future__ import annotations
import logging
from celery import Celery
from app.config import settings

log = logging.getLogger(__name__)

# Оставляем создание приложения Celery, оно может понадобиться для ачивок
celery_app = Celery(
    "ai-friend",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    task_serializer='json',
    result_serializer='json',
    accept_content=['json']
)

# Убираем расписание Beat, т.к. нет задач по расписанию в MVP
# celery_app.conf.beat_schedule = {}
celery_app.conf.timezone = 'UTC'

# --- ЗАДАЧИ УДАЛЕНЫ ---

__all__ = ["celery_app"]
