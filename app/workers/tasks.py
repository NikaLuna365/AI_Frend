# /app/app/workers/tasks.py (Полная исправленная версия)

from __future__ import annotations

import asyncio
import logging
import base64
import tempfile
import os
import sqlalchemy as sa # Убедимся, что импортирован

# --- Импорты Celery ---
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
# Типы для аннотаций
from typing import Optional, List, Sequence, Any # Добавляем нужные типы

log = get_task_logger(__name__)

# --- Инициализация Celery с переменными из settings ---
celery_app = Celery(
    "ai-friend",
    broker=settings.CELERY_BROKER_URL, # Используем значение из настроек
    backend=settings.CELERY_RESULT_BACKEND, # Используем значение из настроек
    include=['app.workers.tasks'], # Список модулей с задачами для автообнаружения
    task_serializer='json',
    result_serializer='json',
    accept_content=['json']
)
# ----------------------------------------------------

# --- Конфигурация Celery ---
celery_app.conf.update(
    task_track_started=True,
    timezone = 'UTC',
    # Опционально: настройки видимости задач и т.д.
    # broker_connection_retry_on_startup=True, # Повторять подключение к брокеру при старте
)

# --- Расписание Beat (Закомментировано/Пустое для MVP) ---
# celery_app.conf.beat_schedule = {}

# --------------------------------------------------------------------------
# Задача Генерации Ачивки
# --------------------------------------------------------------------------

# --- Внутренняя асинхронная логика для генерации ачивки ---
async def _run_generate_achievement_logic(
    task_instance, # Экземпляр задачи Celery (из bind=True)
    user_id: str,
    achievement_code: str,
    theme: str | None = "A generic positive achievement"
    ) -> str:
    """Содержит основную асинхронную логику задачи генерации ачивки."""
    task_id = task_instance.request.id
    log.info(f">>> [_run_achv_logic START] Task ID: {task_id} for user '{user_id}', code '{achievement_code}'")
    gcs_client: storage.Client | None = None
    achievement_status = "FAILED" # Статус по умолчанию

    try:
        # Инициализация клиентов внутри задачи (можно оптимизировать)
        llm = LLMClient()
        gcs_client = storage.Client()
        log.debug(f"[_run_achv_logic {task_id}] GCS Client initialized.")

        async with async_session_context() as session:
            log.debug(f"[_run_achv_logic {task_id}] DB Session created.")
            # Находим правило ачивки
            stmt_rule = sa.select(AchievementRule).where(AchievementRule.code == achievement_code)
            rule = (await session.execute(stmt_rule)).scalar_one_or_none()
            if not rule:
                 log.error(f"[_run_achv_logic {task_id}] AchievementRule '{achievement_code}' not found. Ignoring task.")
                 raise Ignore() # Не повторять задачу

            # Находим существующую запись Achievement (предполагаем, что она создана с status='PENDING')
            stmt_ach = sa.select(Achievement).where(Achievement.user_id == user_id, Achievement.code == achievement_code)
            achievement = (await session.execute(stmt_ach)).scalar_one_or_none()
            if not achievement:
                 log.error(f"[_run_achv_logic {task_id}] Achievement record for user '{user_id}', code '{achievement_code}' not found. Ignoring task.")
                 raise Ignore() # Не повторять

            # Проверяем, не сгенерирована ли уже ачивка полностью
            # Обновляем поле для URL иконки на badge_png_url
            if achievement.badge_png_url and achievement.title != "PENDING_GENERATION": # Используем константу или проверяем на None/default
                 log.warning(f"[_run_achv_logic {task_id}] Achievement user '{user_id}', code '{achievement_code}' already seems generated. Skipping.")
                 return f"ALREADY_GENERATED:{achievement.id}"

            # --- Шаг 1: Генерация Названия ---
            log.info(f"[_run_achv_logic {task_id}] Generating title...")
            # Параметры для генерации названия
            name_gen_context = theme or rule.generation_context or rule.description or rule.title # Берем лучший доступный контекст
            name_style_id = "general_playful" # Пример
            name_tone_hint = "Playful, Positive, Encouraging, Short"
            name_style_examples = "1. Welcome Aboard!\n2. Milestone Reached\n3. First Step!"
            generated_names = await llm.generate_achievement_name(
                context=name_gen_context,
                style_id=name_style_id,
                tone_hint=name_tone_hint,
                style_examples=name_style_examples
            )
            achievement_title = generated_names[0] # Берем первый вариант
            log.info(f"[_run_achv_logic {task_id}] Title generated: '{achievement_title}'")

            # --- Шаг 2: Генерация Иконки (PNG) ---
            log.info(f"[_run_achv_logic {task_id}] Generating icon via Imagen...")
            # Параметры для генерации иконки
            icon_gen_context = theme or rule.title # Используем тему/название для иконки
            icon_style_id = "flat_cartoon" # Пример
            icon_style_keywords = "flat design, simple vector art style, bold outline, vibrant solid colors, no gradients, no shadows, centered emblem"
            icon_palette_hint = "blue, yellow, white, black outline" # Пример
            icon_shape_hint = "circle"
            icon_png_bytes: bytes | None = None # Инициализируем
            try:
                 icon_png_bytes = await llm.generate_achievement_icon(
                      context=icon_gen_context,
                      style_id=icon_style_id,
                      style_keywords=icon_style_keywords,
                      palette_hint=icon_palette_hint,
                      shape_hint=icon_shape_hint
                 )
                 if not icon_png_bytes:
                      log.warning(f"[_run_achv_logic {task_id}] Imagen returned empty bytes for the icon.")
                 else:
                      log.info(f"[_run_achv_logic {task_id}] Icon PNG generated ({len(icon_png_bytes)} bytes).")
            except NotImplementedError:
                 log.warning(f"[_run_achv_logic {task_id}] Icon generation not implemented in provider.")
            except Exception as e_img:
                 log.exception(f"[_run_achv_logic {task_id}] Failed to generate icon via Imagen: {e_img}")
                 # Не прерываем задачу, просто не будет иконки

            # --- Шаг 3: Загрузка Иконки в GCS ---
            badge_png_url: str | None = None # Инициализируем
            if icon_png_bytes and gcs_client and settings.GCS_BUCKET_NAME:
                log.info(f"[_run_achv_logic {task_id}] Uploading icon to GCS bucket '{settings.GCS_BUCKET_NAME}'...")
                try:
                    bucket = gcs_client.bucket(settings.GCS_BUCKET_NAME)
                    blob_name = f"badges/{user_id}/{achievement_code}_{task_id[:8]}.png" # Уникальное имя файла
                    blob = bucket.blob(blob_name)

                    # Используем run_in_executor для синхронного метода SDK
                    loop = asyncio.get_running_loop()
                    await loop.run_in_executor(
                        None,
                        lambda: blob.upload_from_string(icon_png_bytes, content_type='image/png')
                    )
                    # Делаем файл публичным для простоты доступа (настройте ACL бакета!)
                    await loop.run_in_executor(None, blob.make_public)
                    badge_png_url = blob.public_url # Получаем публичный URL
                    log.info(f"[_run_achv_logic {task_id}] Icon uploaded to GCS: {badge_png_url}")
                except GoogleAPICallError as e_gcs:
                    log.exception(f"[_run_achv_logic {task_id}] Failed to upload icon to GCS: {e_gcs}")
                except Exception as e_gcs_other:
                     log.exception(f"[_run_achv_logic {task_id}] Unexpected error uploading icon to GCS: {e_gcs_other}")
            elif icon_png_bytes:
                 log.warning(f"[_run_achv_logic {task_id}] Cannot upload icon: GCS client or bucket name not configured.")


            # --- Шаг 4: Обновление Записи Achievement в БД ---
            log.info(f"[_run_achv_logic {task_id}] Updating achievement record in DB...")
            achievement.title = achievement_title # Обновляем название
            achievement.badge_png_url = badge_png_url # Обновляем URL иконки (может быть None)
            # achievement.status = "COMPLETED" # Обновляем статус, если есть
            achievement.updated_at = func.now() # Обновляем время

            session.add(achievement)
            # Коммитим только изменения этой ачивки
            await session.commit()
            log.info(f"[_run_achv_logic {task_id}] Achievement record id={achievement.id} updated successfully.")
            achievement_status = "COMPLETED"

    except Ignore:
        log.warning(f"[_run_achv_logic {task_id}] Task ignored.")
        achievement_status = "IGNORED"
    except Exception as exc:
        log.exception(f"[_run_achv_logic {task_id}] Unhandled exception: {exc}")
        # Позволяем Celery обработать retry
        raise exc

    finally:
        log.debug(f"[_run_achv_logic {task_id}] Finished with status: {achievement_status}")

    # Возвращаем статус для информации
    return f"{achievement_status}:{achievement_code}:{user_id}"


# --- Основная задача Celery (теперь снова async def) ---
# Убираем обертку asyncio.run, т.к. Celery 5+ должен уметь работать с async def
# Если возникнут проблемы с event loop, вернем обертку
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
    """
    Асинхронная Celery задача для генерации ачивки (обертка для _run_...).
    """
    # Просто вызываем основную асинхронную логику
    return await _run_generate_achievement_logic(self, user_id, achievement_code, theme)

# --- Экспорты ---
__all__ = ["celery_app", "generate_achievement_task"]
