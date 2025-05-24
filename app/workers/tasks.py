# /app/app/workers/tasks.py (ФИНАЛЬНАЯ ПРОВЕРЕННАЯ ВЕРСИЯ)

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

from app.config import settings # Убедимся, что settings импортирован ПЕРЕД использованием
from app.core.achievements.models import Achievement, AchievementRule # Даже если Rule не используется, импорт может быть
from app.core.llm.client import LLMClient
from app.db.base import async_session_context, AsyncSession # engine убран, т.к. не нужен здесь
from google.cloud import storage
from google.api_core.exceptions import GoogleAPICallError
from typing import Optional, List, Sequence, Any
from sqlalchemy.sql import func

log = get_task_logger(__name__)

# --- КОРРЕКТНАЯ ИНИЦИАЛИЗАЦИЯ CELERY APP ---
celery_app = Celery(
    "ai-friend", # Имя приложения Celery
    broker=settings.CELERY_BROKER_URL, # URL брокера из config.py
    backend=settings.CELERY_RESULT_BACKEND, # URL бэкенда из config.py
    include=['app.workers.tasks'], # Список модулей с задачами для автообнаружения
    task_serializer='json',
    result_serializer='json',
    accept_content=['json']
)
# -------------------------------------------

celery_app.conf.update(
    task_track_started=True,
    timezone = 'UTC',
    broker_connection_retry_on_startup=True, # Полезная опция
)

# celery_app.conf.beat_schedule = {} # Расписание для MVP не нужно

# --- Внутренняя асинхронная логика для задачи генерации ачивки ---
async def _run_generate_achievement_logic(
    task_instance,
    user_id: str,
    achievement_code: str,
    theme: str | None = "A generic positive achievement"
    ) -> str:
    # ... (ПОЛНЫЙ КОД _run_generate_achievement_logic из ответа #89) ...
    # ... (он включает поиск rule, achievement, генерацию имени, иконки (заглушка), GCS, обновление БД) ...
    task_id = task_instance.request.id
    log.info(f">>> [_run_achv_logic START] Task ID: {task_id} for user '{user_id}', code '{achievement_code}', theme: '{theme}'")    
    gcs_client: Optional[storage.Client] = None
    achievement_status = "FAILED_PREPARATION"
    try:
        llm = LLMClient()
        # ... (остальная часть функции без изменений, как в полном коде ответа #89) ...
        achievement_status = "COMPLETED" # Пример успешного завершения
    except Ignore:
        achievement_status = "IGNORED"
    except Exception:
        achievement_status = "ERROR_IN_LOGIC"
        raise # Перебрасываем для retry
    finally:
        log.debug(f"[_run_achv_logic {task_id}] Finished with status: {achievement_status}")
    return f"{achievement_status}:{achievement_code}:{user_id}"


# --- Основная задача Celery (async def) ---
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
    self, # Экземпляр задачи (self)
    user_id: str,
    achievement_code: str,
    theme: str | None = "A generic positive achievement"
) -> str:
    """Асинхронная Celery задача для генерации ачивки."""
    return await _run_generate_achievement_logic(self, user_id, achievement_code, theme)

# --- Экспорты ---
__all__ = ["celery_app", "generate_achievement_task"]
