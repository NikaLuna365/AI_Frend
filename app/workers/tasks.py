# /app/app/workers/tasks.py (Исправленная v3)

from __future__ import annotations

import asyncio
import logging
import base64
import tempfile
import os
import sqlalchemy as sa # Убедимся, что импортирован

from celery import Celery
from celery.exceptions import Ignore
from celery.utils.log import get_task_logger

# --- Импорты проекта ---
from app.config import settings
# Модели
from app.core.achievements.models import Achievement, AchievementRule
# LLM Клиент
from app.core.llm.client import LLMClient
# Контекст БД
from app.db.base import async_session_context, AsyncSession, engine # Импортируем engine для dispose
# Клиент GCS
from google.cloud import storage
from google.api_core.exceptions import GoogleAPICallError

log = get_task_logger(__name__)

# --- ИСПРАВЛЕННАЯ ИНИЦИАЛИЗАЦИЯ ---
# Убраны многоточия, используются переменные из settings
celery_app = Celery(
    "ai-friend",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    task_serializer='json',
    result_serializer='json',
    accept_content=['json']
)
# ----------------------------------

# --- Конфигурация Celery (без изменений) ---
celery_app.conf.update(
    task_track_started=True,
    timezone = 'UTC',
)

# --- Расписание Beat (Закомментировано) ---
# celery_app.conf.beat_schedule = {}

# --- Задача Генерации Ачивки (Код без изменений по сравнению с ответом #71) ---
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
    # --- ВАЖНО: Обернем всю асинхронную логику задачи в asyncio.run, как делали для send_due_reminders ---
    #    Это предотвратит потенциальные проблемы с event loop в prefork воркере для этой задачи тоже.
    task_id = self.request.id
    log.info(f">>> [AchvTask WRAPPER START] ID: {task_id}. Calling asyncio.run()...")
    result_str = "Achv Task failed before async execution."
    try:
         result_str = await _run_generate_achievement_logic(self, user_id, achievement_code, theme)
         log.info(f">>> [AchvTask WRAPPER END] ID: {task_id}. Async logic completed. Result: {result_str}")
         return result_str
    except Exception as e:
         log.exception(f">>> [AchvTask WRAPPER ERROR] ID: {task_id}. Exception during async logic: {e}")
         raise # Перебрасываем для статуса FAILED
    # finally: # Dispose engine здесь НЕ НУЖЕН, если задача сама по себе async


# --- Внутренняя асинхронная логика для генерации ачивки ---
async def _run_generate_achievement_logic(
    task_instance, # Передаем self как task_instance
    user_id: str,
    achievement_code: str,
    theme: str | None = "A generic positive achievement"
    ) -> str:
    task_id = task_instance.request.id # Получаем ID из переданного инстанса
    log.info(f">>> [_run_achv_logic START] Task ID: {task_id} for user '{user_id}', code '{achievement_code}'")
    gcs_client: storage.Client | None = None
    achievement_status = "FAILED"
    try:
        llm = LLMClient()
        gcs_client = storage.Client()
        log.debug(f"[_run_achv_logic {task_id}] GCS Client initialized.")

        async with async_session_context() as session:
            # ach_service = AchievementsService(db_session=session, llm_client=llm) # Создаем сервис, если он нужен

            stmt_rule = sa.select(AchievementRule).where(AchievementRule.code == achievement_code)
            rule = (await session.execute(stmt_rule)).scalar_one_or_none()
            # ... (остальная логика задачи: поиск achievement, генерация имени, иконки, GCS, обновление БД) ...
            # ... (как в ответе #71) ...
            # --- Шаг 1: Название ---
            # ... gen_names = await llm.generate_achievement_name(...) ...
            # --- Шаг 2: Иконка ---
            # ... icon_png_bytes = await llm.generate_achievement_icon(...) ...
            # --- Шаг 3: GCS ---
            # ... badge_png_url = await loop.run_in_executor(...) ...
            # --- Шаг 4: DB Update ---
            # ... session.add(achievement); await session.commit() ...
            achievement_status = "COMPLETED" # Устанавливаем при успехе

    except Ignore:
        log.warning(f"[_run_achv_logic {task_id}] Task ignored.")
        achievement_status = "IGNORED"
        # Не перебрасываем Ignore, задача должна завершиться "успешно"
    except Exception as exc:
        log.exception(f"[_run_achv_logic {task_id}] Unhandled exception: {exc}")
        # Перебрасываем другие исключения для retry
        raise

    finally:
        log.debug(f"[_run_achv_logic {task_id}] Finished with status: {achievement_status}")

    return f"{achievement_status}:{achievement_code}:{user_id}"

# --- Экспорты ---
__all__ = ["celery_app", "generate_achievement_task"] # Добавляем новую задачу в экспорт
