# /app/app/workers/tasks.py (ФИНАЛЬНАЯ ВЕРСИЯ БЕЗ AchievementRule в логике)

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
# --- ИСПРАВЛЕНИЕ: Импортируем ТОЛЬКО Achievement ---
from app.core.achievements.models import Achievement # AchievementRule НЕ НУЖНА
# ---------------------------------------------
from app.core.llm.client import LLMClient
from app.db.base import async_session_context, AsyncSession
from google.cloud import storage
from google.api_core.exceptions import GoogleAPICallError
from typing import Optional, List, Sequence, Any

log = get_task_logger(__name__)
celery_app = Celery(...) # Полное определение, как в #89

async def _run_generate_achievement_logic(
    task_instance, user_id: str, achievement_code: str, theme: str | None
    ) -> str:
    task_id = task_instance.request.id
    log.info(f">>> [_run_achv_logic START] Task ID: {task_id} for user '{user_id}', code '{achievement_code}', theme: '{theme}'")
    achievement_status = "FAILED_PREPARATION"
    try:
        llm = LLMClient()
        gcs_client: Optional[storage.Client] = None
        if settings.GCS_BUCKET_NAME:
            try:
                gcs_client = storage.Client()
                log.debug(f"[_run_achv_logic {task_id}] GCS Client initialized.")
            except Exception as e_gcs_init:
                log.exception(f"[_run_achv_logic {task_id}] Failed to initialize GCS client: {e_gcs_init}")

        async with async_session_context() as session:
            # --- УБИРАЕМ ПОИСК AchievementRule ---
            # rule = (await session.execute(sa.select(AchievementRule)...)).scalar_one_or_none()
            # if not rule: raise Ignore()
            # ------------------------------------
            actual_theme_for_generation = theme or "a significant accomplishment" # Используем переданную тему

            stmt_ach = sa.select(Achievement).where(Achievement.user_id == user_id, Achievement.code == achievement_code)
            achievement = (await session.execute(stmt_ach)).scalar_one_or_none()
            if not achievement:
                 log.error(f"[_run_achv_logic {task_id}] Achievement record '{achievement_code}' for user '{user_id}' not found. Ignoring.")
                 raise Ignore()
            if achievement.status == "COMPLETED":
                 log.warning(f"[_run_achv_logic {task_id}] Achievement '{achievement_code}' for user '{user_id}' already COMPLETED. Skipping.")
                 return f"ALREADY_COMPLETED:{achievement.id}"

            achievement.status = "PROCESSING" # Обновляем статус перед долгой операцией
            achievement.title = "Generating..." # Временный заголовок
            session.add(achievement)
            await session.commit() # Коммитим PENDING/PROCESSING статус

            # Генерация Названия
            log.info(f"[_run_achv_logic {task_id}] Generating title using theme: '{actual_theme_for_generation}'")
            # ... (параметры для generate_achievement_name) ...
            generated_names = await llm.generate_achievement_name(
                context=actual_theme_for_generation, style_id="default_game_style", ...
            )
            achievement_title = generated_names[0] if generated_names else f"{achievement_code.replace('_',' ').title()}"
            log.info(f"[_run_achv_logic {task_id}] Title generated: '{achievement_title}'")

            # Генерация Иконки
            log.info(f"[_run_achv_logic {task_id}] Generating icon using theme: '{actual_theme_for_generation}'")
            # ... (параметры для generate_achievement_icon) ...
            icon_png_bytes = await llm.generate_achievement_icon(
                context=actual_theme_for_generation, style_id="flat_badge_icon", ...
            )
            # ... (логика загрузки в GCS) ...
            badge_png_url = None # Заглушка
            if icon_png_bytes and gcs_client and settings.GCS_BUCKET_NAME:
                # ... (код загрузки в GCS) ...
                badge_png_url = "http://example.com/dummy_badge.png" # Заменить реальным URL
            
            # Обновление БД
            achievement.title = achievement_title
            achievement.badge_png_url = badge_png_url
            achievement.status = "COMPLETED"
            achievement.updated_at = func.now()
            session.add(achievement)
            await session.commit()
            achievement_status = "COMPLETED"

    except Ignore:
        achievement_status = "IGNORED"; log.warning(...)
    except Exception as exc:
        achievement_status = "ERROR_IN_LOGIC"; log.exception(...)
        # Попытка обновить статус ачивки на FAILED_GENERATION
        try:
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
        raise # Перебрасываем исходное исключение для retry Celery
    finally:
        log.debug(...)
    return f"{achievement_status}:{achievement_code}:{user_id}"

# Основная задача (без изменений)
@celery_app.task(...)
async def generate_achievement_task(...):
    return await _run_generate_achievement_logic(...)

__all__ = ["celery_app", "generate_achievement_task"]
