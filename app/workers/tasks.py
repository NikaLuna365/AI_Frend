# /app/app/workers/tasks.py (Исправляем импорт)

from __future__ import annotations

import asyncio
import logging
import base64
import tempfile
import os
import sqlalchemy as sa
from sqlalchemy.sql import func # Убедимся, что func импортирован

from celery import Celery
from celery.exceptions import Ignore
from celery.utils.log import get_task_logger

from app.config import settings
# --- ИСПРАВЛЕНИЕ: Импортируем ТОЛЬКО Achievement ---
from app.core.achievements.models import Achievement # Убрали AchievementRule
# ---------------------------------------------
from app.core.llm.client import LLMClient
from app.db.base import async_session_context, AsyncSession
from google.cloud import storage
from google.api_core.exceptions import GoogleAPICallError
from typing import Optional, List, Sequence, Any

log = get_task_logger(__name__)

# Инициализация Celery (оставляем как есть, уже исправлено)
celery_app = Celery(
    "ai-friend",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=['app.workers.tasks'],
    task_serializer='json',
    result_serializer='json',
    accept_content=['json']
)

celery_app.conf.update(
    task_track_started=True,
    timezone = 'UTC',
    broker_connection_retry_on_startup=True,
)

# celery_app.conf.beat_schedule = {}

# --- Внутренняя асинхронная логика для задачи (без AchievementRule) ---
async def _run_generate_achievement_logic(
    task_instance, user_id: str, achievement_code: str, theme: str | None
    ) -> str:
    task_id = task_instance.request.id
    log.info(f">>> [_run_achv_logic START] Task ID: {task_id} for user '{user_id}', code '{achievement_code}', theme: '{theme}'")
    # ... (остальной код _run_generate_achievement_logic без использования AchievementRule)
    # ... (поиск rule по AchievementRule УБРАН)
    # ... (actual_theme берется из theme или дефолта)
    # ... (все вызовы к llm.generate_achievement_name/icon используют actual_theme)
    gcs_client: Optional[storage.Client] = None
    achievement_status = "FAILED_PREPARATION"
    try:
        llm = LLMClient()
        # ... (инициализация gcs_client) ...

        async with async_session_context() as session:
            log.debug(f"[_run_achv_logic {task_id}] DB Session created.")
            actual_theme_for_generation = theme or "a significant accomplishment"

            stmt_ach = sa.select(Achievement).where(Achievement.user_id == user_id, Achievement.code == achievement_code)
            achievement = (await session.execute(stmt_ach)).scalar_one_or_none()
            if not achievement:
                 log.error(f"[_run_achv_logic {task_id}] Achievement record '{achievement_code}' for user '{user_id}' not found. Ignoring.")
                 raise Ignore()
            if achievement.status == "COMPLETED":
                 log.warning(f"[_run_achv_logic {task_id}] Achievement '{achievement_code}' for user '{user_id}' already COMPLETED. Skipping.")
                 return f"ALREADY_COMPLETED:{achievement.id}"

            achievement.status = "PROCESSING"
            achievement.title = "Generating..."
            session.add(achievement)
            await session.commit() # Коммитим PENDING/PROCESSING статус

            # Генерация Названия
            log.info(f"[_run_achv_logic {task_id}] Generating title using theme: '{actual_theme_for_generation}'")
            # ... (параметры для generate_achievement_name) ...
            generated_names = await llm.generate_achievement_name(context=actual_theme_for_generation, ...)
            achievement_title = generated_names[0] if generated_names else f"{achievement_code.replace('_',' ').title()}"

            # Генерация Иконки
            log.info(f"[_run_achv_logic {task_id}] Generating icon using theme: '{actual_theme_for_generation}'")
            icon_png_bytes = await llm.generate_achievement_icon(context=actual_theme_for_generation, ...)
            
            badge_png_url = None
            if icon_png_bytes and gcs_client and settings.GCS_BUCKET_NAME:
                # ... (код загрузки в GCS) ...
                badge_png_url = "http://example.com/dummy_badge.png" # Заменить
            
            # Обновление БД
            achievement.title = achievement_title
            achievement.badge_png_url = badge_png_url
            achievement.status = "COMPLETED"
            achievement.updated_at = func.now()
            session.add(achievement)
            await session.commit()
            achievement_status = "COMPLETED"
    # ... (обработка Ignore, Exception, finally) ...
    except Ignore: achievement_status = "IGNORED"; log.warning(f"[_run_achv_logic {task_id}] Task ignored.")
    except Exception as exc: achievement_status = "ERROR_IN_LOGIC"; log.exception(f"[_run_achv_logic {task_id}] Unhandled: {exc}"); raise
    finally: log.debug(f"[_run_achv_logic {task_id}] Finished with status: {achievement_status}")
    return f"{achievement_status}:{achievement_code}:{user_id}"

# Основная задача Celery
@celery_app.task(...) # Все параметры retry остаются
async def generate_achievement_task(...):
    return await _run_generate_achievement_logic(...)

__all__ = ["celery_app", "generate_achievement_task"]
