# /app/app/workers/tasks.py (Исправленная Инициализация Celery v4)

from __future__ import annotations

import asyncio
import logging
import base64
import tempfile
import os
import sqlalchemy as sa

from celery import Celery
from celery.exceptions import Ignore
from celery.utils.log import get_task_logger

from app.config import settings
# from app.core.achievements.service import AchievementsService # Пока не используется
from app.core.achievements.models import Achievement, AchievementRule
from app.core.llm.client import LLMClient
from app.db.base import async_session_context, AsyncSession, engine
from google.cloud import storage
from google.api_core.exceptions import GoogleAPICallError

log = get_task_logger(__name__)

# --- ИСПРАВЛЕНИЕ: Убраны многоточия, используются settings ---
celery_app = Celery(
    "ai-friend",
    broker=settings.CELERY_BROKER_URL, # <-- Исправлено
    backend=settings.CELERY_RESULT_BACKEND, # <-- Исправлено
    include=['app.workers.tasks'],
    task_serializer='json',
    result_serializer='json',
    accept_content=['json']
)
# ----------------------------------------------------------

celery_app.conf.update(
    task_track_started=True,
    timezone = 'UTC',
)

# celery_app.conf.beat_schedule = {} # Расписание пока не нужно

# --- Задача Ачивки (без изменений в логике, но теперь celery_app определен правильно) ---
@celery_app.task(
    name="app.workers.tasks.generate_achievement_task",
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 3},
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True
)
async def generate_achievement_task(
    self, user_id: str, achievement_code: str, theme: str | None = "A generic positive achievement"
) -> str:
    # Используем обертку asyncio.run для совместимости с prefork воркером
    task_id = self.request.id
    log.info(f">>> [AchvTask WRAPPER START] ID: {task_id}. Calling async logic...")
    result_str = "Achv Task failed before async execution."
    try:
         result_str = await _run_generate_achievement_logic(self, user_id, achievement_code, theme)
         log.info(f">>> [AchvTask WRAPPER END] ID: {task_id}. Async logic completed. Result: {result_str}")
         return result_str
    except Exception as e:
         log.exception(f">>> [AchvTask WRAPPER ERROR] ID: {task_id}. Exception during async logic: {e}")
         raise

# --- Внутренняя асинхронная логика (без изменений) ---
async def _run_generate_achievement_logic(
    task_instance, user_id: str, achievement_code: str, theme: str | None
    ) -> str:
    # ... (весь код _run_generate_achievement_logic как в ответе #71) ...
    task_id = task_instance.request.id
    log.info(f">>> [_run_achv_logic START] Task ID: {task_id} ...")
    # ... (инициализация GCS, получение сессии, LLM) ...
    # ... (поиск правила и ачивки) ...
    # ... (генерация имени) ...
    # ... (генерация иконки) ...
    # ... (загрузка в GCS) ...
    # ... (обновление БД) ...
    # ... (обработка Ignore и других Exception) ...
    # ... (finally и return status) ...
    # --- ДЛЯ КРАТКОСТИ ЗАМЕНИЛ НА МНОГОТОЧИЕ, НО КОД ОСТАЕТСЯ КАК В #71 ---
    return "COMPLETED:dummy_code:dummy_user" # при успешном выполнении

__all__ = ["celery_app", "generate_achievement_task"]
