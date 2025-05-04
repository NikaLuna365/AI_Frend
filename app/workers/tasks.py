# /app/app/workers/tasks.py (Исправленная инициализация celery_app)

from __future__ import annotations

import asyncio
import logging
import base64
import tempfile
import os
import sqlalchemy as sa # <-- ДОБАВЛЕН импорт sa для запроса

from celery import Celery
from celery.exceptions import Ignore
from celery.utils.log import get_task_logger

# --- Импорты проекта ---
from app.config import settings
# Сервис Ачивок (для обновления статуса/данных) - пока не используем напрямую в задаче
# from app.core.achievements.service import AchievementsService
# Модели
from app.core.achievements.models import Achievement, AchievementRule
# LLM Клиент
from app.core.llm.client import LLMClient
# Контекст БД
from app.db.base import async_session_context, AsyncSession
# Клиент GCS
from google.cloud import storage
from google.api_core.exceptions import GoogleAPICallError

log = get_task_logger(__name__)

# --- ИСПРАВЛЕНИЕ: Инициализируем Celery с переменными из settings ---
celery_app = Celery(
    "ai-friend",
    broker=settings.CELERY_BROKER_URL, # Используем значение из настроек
    backend=settings.CELERY_RESULT_BACKEND, # Используем значение из настроек
    task_serializer='json',
    result_serializer='json',
    accept_content=['json']
)
# --------------------------------------------------------------------

# Конфигурация Celery
celery_app.conf.update(
    task_track_started=True,
    timezone = 'UTC',
)

# Расписание Beat (пустое для MVP)
# celery_app.conf.beat_schedule = {}

# --- Задача Генерации Ачивки (Код без изменений, но убедимся, что sa импортирован для stmt_rule/stmt_ach) ---
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
    task_id = self.request.id
    log.info(f"[AchvTask {task_id}] Starting generation for user '{user_id}', code '{achievement_code}', theme '{theme}'")
    gcs_client: storage.Client | None = None
    achievement_status = "FAILED"
    try:
        llm = LLMClient()
        gcs_client = storage.Client()
        log.debug(f"[AchvTask {task_id}] GCS Client initialized.")

        async with async_session_context() as session:
            # ach_service = AchievementsService(db_session=session, llm_client=llm) # Создаем сервис, если он нужен

            # Используем sa (импортирован в начале файла)
            stmt_rule = sa.select(AchievementRule).where(AchievementRule.code == achievement_code)
            rule = (await session.execute(stmt_rule)).scalar_one_or_none()
            if not rule:
                 log.error(f"[AchvTask {task_id}] Rule '{achievement_code}' not found. Ignoring.")
                 raise Ignore()

            stmt_ach = sa.select(Achievement).where(Achievement.user_id == user_id, Achievement.code == achievement_code)
            achievement = (await session.execute(stmt_ach)).scalar_one_or_none()
            if not achievement:
                 log.error(f"[AchvTask {task_id}] Achievement record not found. Ignoring.")
                 raise Ignore()

            # ... (остальная логика задачи: генерация имени, иконки, GCS, обновление БД) ...
            # ... (как в предыдущем ответе) ...
            # --- Шаг 1: Генерация Названия ---
            log.info(f"[AchvTask {task_id}] Generating title...")
            tone_hint = "Playful, Positive, Encouraging"
            style_examples = "1. Welcome Aboard!\n2. Milestone Reached\n3. First Step!"
            gen_names = await llm.generate_achievement_name(...) # Передаем параметры
            achievement_title = gen_names[0]
            log.info(f"[AchvTask {task_id}] Title generated: '{achievement_title}'")

            # --- Шаг 2: Генерация Иконки ---
            log.info(f"[AchvTask {task_id}] Generating icon via Imagen...")
            # ... (параметры стиля) ...
            icon_png_bytes = await llm.generate_achievement_icon(...) # Передаем параметры
            if icon_png_bytes: log.info(f"[AchvTask {task_id}] Icon PNG generated.")
            else: log.warning(f"[AchvTask {task_id}] Icon generation failed or skipped.")

            # --- Шаг 3: Загрузка в GCS ---
            badge_png_url = None
            if icon_png_bytes and gcs_client:
                 # ... (логика загрузки в GCS) ...
                 badge_png_url = blob.public_url
                 log.info(f"[AchvTask {task_id}] Icon uploaded to GCS: {badge_png_url}")

            # --- Шаг 4: Обновление БД ---
            log.info(f"[AchvTask {task_id}] Updating achievement record...")
            achievement.title = achievement_title
            # ИСПРАВЛЕНИЕ: Используем правильное имя поля из модели Achievement
            achievement.badge_png_url = badge_png_url # Убедитесь, что поле называется так
            achievement.updated_at = func.now()
            session.add(achievement)
            await session.commit()
            log.info(f"[AchvTask {task_id}] Achievement record updated.")
            achievement_status = "COMPLETED"

    except Ignore:
        log.warning(f"[AchvTask {task_id}] Task ignored.")
        achievement_status = "IGNORED"
    except Exception as exc:
        log.exception(f"[AchvTask {task_id}] Unhandled exception: {exc}")
        raise # Перебрасываем для retry Celery
    finally:
        log.debug(f"[AchvTask {task_id}] Task finished with status: {achievement_status}")

    return f"{achievement_status}:{achievement_code}:{user_id}"

# --- Экспорты ---
__all__ = ["celery_app", "generate_achievement_task"]
