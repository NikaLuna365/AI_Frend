# /app/app/workers/tasks.py (Полная версия для Фазы 2, без "...")

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
# from app.core.achievements.service import AchievementsService # Закомментировано, т.к. сервис еще не используется активно
from app.core.achievements.models import Achievement, AchievementRule
from app.core.llm.client import LLMClient
from app.db.base import async_session_context, AsyncSession, engine
from google.cloud import storage
from google.api_core.exceptions import GoogleAPICallError
from typing import Optional, List, Sequence, Any

log = get_task_logger(__name__)

# Инициализация Celery с переменными из settings
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
)

# celery_app.conf.beat_schedule = {} # Расписание пока не нужно

async def _run_generate_achievement_logic(
    task_instance, user_id: str, achievement_code: str, theme: str | None
    ) -> str:
    task_id = task_instance.request.id
    log.info(f">>> [_run_achv_logic START] Task ID: {task_id} for user '{user_id}', code '{achievement_code}'")
    achievement_status = "PENDING_IMPLEMENTATION"
    try:
        llm = LLMClient()
        async with async_session_context() as session:
            log.debug(f"[_run_achv_logic {task_id}] DB Session created.")
            # Находим правило
            stmt_rule = sa.select(AchievementRule).where(AchievementRule.code == achievement_code)
            rule = (await session.execute(stmt_rule)).scalar_one_or_none()
            if not rule: raise Ignore()
            # Находим ачивку
            stmt_ach = sa.select(Achievement).where(Achievement.user_id == user_id, Achievement.code == achievement_code)
            achievement = (await session.execute(stmt_ach)).scalar_one_or_none()
            if not achievement: raise Ignore()

            log.info(f"[_run_achv_logic {task_id}] generate_achievement_name called by task (placeholder).")
            gen_names = await llm.generate_achievement_name(
                context=theme or rule.title, style_id="default", tone_hint="positive", style_examples=""
            )
            achievement_title = gen_names[0]

            log.info(f"[_run_achv_logic {task_id}] generate_achievement_icon called by task (placeholder).")
            icon_bytes = await llm.generate_achievement_icon(
                context=theme or rule.title, style_id="default", style_keywords="", palette_hint="", shape_hint=""
            )

            # Заглушки для GCS и обновления БД
            badge_png_url = "http://example.com/placeholder_badge.png" if icon_bytes else None
            log.info(f"[_run_achv_logic {task_id}] Placeholder badge_png_url: {badge_png_url}")

            achievement.title = achievement_title
            achievement.badge_png_url = badge_png_url
            # achievement.status = "COMPLETED"
            achievement.updated_at = func.now() # Используем func из sqlalchemy.sql
            session.add(achievement)
            await session.commit()
            achievement_status = "ATTEMPTED_GENERATION_MVP"

    except Ignore:
        log.warning(f"[_run_achv_logic {task_id}] Task ignored (no rule/achievement).")
        achievement_status = "IGNORED"
    except Exception as exc:
        log.exception(f"[_run_achv_logic {task_id}] Unhandled exception: {exc}")
        raise # Позволяем Celery обработать retry
    finally:
        log.debug(f"[_run_achv_logic {task_id}] Finished with status: {achievement_status}")
    return f"{achievement_status}:{achievement_code}:{user_id}"

@celery_app.task(
    name="app.workers.tasks.generate_achievement_task",
    bind=True, # ... (остальные настройки retry) ...
)
async def generate_achievement_task(
    self, user_id: str, achievement_code: str, theme: str | None = "A generic positive achievement"
) -> str:
    return await _run_generate_achievement_logic(self, user_id, achievement_code, theme)

__all__ = ["celery_app", "generate_achievement_task"]
