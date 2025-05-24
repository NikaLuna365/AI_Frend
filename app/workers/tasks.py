# /app/workers/tasks.py (ФИНАЛЬНАЯ ИСПРАВЛЕННАЯ ВЕРСИЯ v4)

from __future__ import annotations

import asyncio
import logging
import base64
import tempfile
import os
import sqlalchemy as sa
from sqlalchemy.sql import func

from celery import Celery
from celery.exceptions import Ignore
from celery.utils.log import get_task_logger

from app.config import settings
from app.core.achievements.models import Achievement # Убрали AchievementRule
from app.core.llm.client import LLMClient
from app.db.base import async_session_context, AsyncSession
from google.cloud import storage
from google.api_core.exceptions import GoogleAPICallError
from typing import Optional, List, Sequence, Any

log = get_task_logger(__name__)

# Инициализация Celery (исправлена)
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

async def _run_generate_achievement_logic(
    task_instance,
    user_id: str,
    achievement_code: str,
    theme: str | None = "A generic positive achievement"
    ) -> str:
    task_id = task_instance.request.id
    log.info(f">>> [_run_achv_logic START] Task ID: {task_id} for user '{user_id}', code '{achievement_code}', theme: '{theme}'")
    gcs_client: Optional[storage.Client] = None
    achievement_status = "FAILED_PREPARATION"
    try:
        llm = LLMClient()
        if settings.GCS_BUCKET_NAME:
            try:
                gcs_client = storage.Client()
                log.debug(f"[_run_achv_logic {task_id}] GCS Client initialized.")
            except Exception as e_gcs_init:
                 log.exception(f"[_run_achv_logic {task_id}] Failed to initialize GCS client: {e_gcs_init}")

        async with async_session_context() as session:
            log.debug(f"[_run_achv_logic {task_id}] DB Session created.")
            actual_theme_for_generation = theme or "a significant accomplishment"

            stmt_ach = sa.select(Achievement).where(Achievement.user_id == user_id, Achievement.code == achievement_code)
            achievement = (await session.execute(stmt_ach)).scalar_one_or_none()
            if not achievement:
                 log.info(f"[_run_achv_logic {task_id}] Achievement record for '{achievement_code}' user '{user_id}' not found. Creating new one.")
                 achievement = Achievement(
                     user_id=user_id,
                     code=achievement_code,
                     title="PENDING_GENERATION",
                     status="PENDING_GENERATION",
                 )
                 session.add(achievement)
                 await session.flush() # Чтобы получить ID и убедиться, что запись есть перед коммитом статуса
            elif achievement.status == "COMPLETED":
                 log.warning(f"[_run_achv_logic {task_id}] Achievement '{achievement_code}' for user '{user_id}' already COMPLETED. Skipping.")
                 return f"ALREADY_COMPLETED:{achievement.id}"

            achievement.status = "PROCESSING"
            achievement.title = "Generating..."
            session.add(achievement) # Добавляем в сессию, если создали или изменили
            await session.commit() # Коммитим PENDING/PROCESSING статус

            log.info(f"[_run_achv_logic {task_id}] Generating title using theme: '{actual_theme_for_generation}'")
            name_style_id = "default_game_style"
            name_tone_hint = "Exciting, Short, Memorable"
            name_style_examples = "1. Victory!\n2. Quest Complete!\n3. Legend Born"
            generated_names = await llm.generate_achievement_name(
                context=actual_theme_for_generation, style_id=name_style_id, tone_hint=name_tone_hint, style_examples=name_style_examples
            )
            achievement_title = generated_names[0] if generated_names else f"{achievement_code.replace('_',' ').title()}"
            log.info(f"[_run_achv_logic {task_id}] Title generated: '{achievement_title}'")

            log.info(f"[_run_achv_logic {task_id}] Generating icon (placeholder) using theme: '{actual_theme_for_generation}'")
            icon_style_id = "flat_badge_icon_v2"
            icon_style_keywords = "minimalist achievement badge, flat design, simple vector art, bold outline"
            icon_palette_hint = "silver, dark_blue, white"
            icon_shape_hint = "shield"
            icon_png_bytes = await llm.generate_achievement_icon(
                context=actual_theme_for_generation, style_id=icon_style_id, style_keywords=icon_style_keywords,
                palette_hint=icon_palette_hint, shape_hint=icon_shape_hint
            ) # Этот метод пока возвращает None

            badge_png_url = None
            if icon_png_bytes and gcs_client and settings.GCS_BUCKET_NAME:
                log.info(f"[_run_achv_logic {task_id}] Uploading icon to GCS bucket '{settings.GCS_BUCKET_NAME}'...")
                try:
                    bucket = gcs_client.bucket(settings.GCS_BUCKET_NAME)
                    blob_name = f"achievements_badges/{user_id}/{achievement_code}_{task_id[:8]}.png"
                    blob = bucket.blob(blob_name)
                    loop = asyncio.get_running_loop()
                    await loop.run_in_executor(None, lambda: blob.upload_from_string(icon_png_bytes, content_type='image/png'))
                    await loop.run_in_executor(None, blob.make_public)
                    badge_png_url = blob.public_url
                    log.info(f"[_run_achv_logic {task_id}] Icon uploaded to GCS: {badge_png_url}")
                except GoogleAPICallError as e_gcs:
                    log.exception(f"[_run_achv_logic {task_id}] GCS API Error during icon upload: {e_gcs}")
                except Exception as e_gcs_other:
                    log.exception(f"[_run_achv_logic {task_id}] Unexpected error uploading icon to GCS: {e_gcs_other}")
            elif icon_png_bytes:
                log.warning(f"[_run_achv_logic {task_id}] Icon generated, but GCS client or bucket name not configured. Skipping upload.")

            achievement.title = achievement_title
            achievement.badge_png_url = badge_png_url
            achievement.status = "COMPLETED"
            achievement.updated_at = func.now()
            session.add(achievement)
            await session.commit()
            achievement_status = "COMPLETED"
            log.info(f"[_run_achv_logic {task_id}] Achievement '{achievement_code}' for user '{user_id}' set to COMPLETED.")

    except Ignore:
        achievement_status = "IGNORED"; log.warning(f"[_run_achv_logic {task_id}] Task ignored.")
    except Exception as exc:
        achievement_status = "ERROR_IN_LOGIC"; log.exception(f"[_run_achv_logic {task_id}] Unhandled: {exc}")
        try: # Попытка обновить статус на FAILED_GENERATION
            async with async_session_context() as error_session:
                stmt_ach_err = sa.select(Achievement).where(Achievement.user_id == user_id, Achievement.code == achievement_code)
                ach_to_fail = (await error_session.execute(stmt_ach_err)).scalar_one_or_none()
                if ach_to_fail and ach_to_fail.status != "COMPLETED":
                    ach_to_fail.status = "FAILED_GENERATION"
                    ach_to_fail.updated_at = func.now()
                    error_session.add(ach_to_fail)
                    await error_session.commit()
                    log.info(f"Marked achievement {achievement_code} for user {user_id} as FAILED_GENERATION.")
        except Exception as db_err_update:
            log.exception(f"Failed to mark achievement as FAILED_GENERATION: {db_err_update}")
        raise
    finally:
        log.debug(f"[_run_achv_logic {task_id}] Finished with status: {achievement_status}")
    return f"{achievement_status}:{achievement_code}:{user_id}"

# --- ИСПРАВЛЕНИЕ: Заменяем ... на реальные аргументы ---
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
    theme: str | None = "A generic positive achievement" # Совпадает с _run_generate_achievement_logic
) -> str:
    """Асинхронная Celery задача для генерации ачивки."""
    return await _run_generate_achievement_logic(self, user_id, achievement_code, theme)
# ----------------------------------------------------

__all__ = ["celery_app", "generate_achievement_task"]
