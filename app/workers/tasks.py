# /app/app/workers/tasks.py (Полная версия для Фазы 2)

from __future__ import annotations

import asyncio
import logging
import base64
import tempfile
import os
import sqlalchemy as sa

from celery import Celery
from celery.exceptions import Ignore # Для ситуаций, когда retry не нужен
from celery.utils.log import get_task_logger # Рекомендуемый логгер для задач

# --- Импорты проекта ---
from app.config import settings
# Модели (для поиска AchievementRule и Achievement)
from app.core.achievements.models import Achievement, AchievementRule
# LLM Клиент (для вызова методов Gemini/Imagen)
from app.core.llm.client import LLMClient
# Контекст БД и тип сессии
from app.db.base import async_session_context, AsyncSession, engine # engine может не понадобиться здесь
# Клиент GCS (если используется напрямую)
from google.cloud import storage
from google.api_core.exceptions import GoogleAPICallError
# Типы для аннотаций
from typing import Optional, List, Sequence, Any

log = get_task_logger(__name__) # Используем логгер Celery

# --- Инициализация Celery с переменными из settings ---
celery_app = Celery(
    "ai-friend", # Имя приложения Celery
    broker=settings.CELERY_BROKER_URL, # URL брокера из config.py
    backend=settings.CELERY_RESULT_BACKEND, # URL бэкенда из config.py
    include=['app.workers.tasks'], # Список модулей с задачами для автообнаружения
    task_serializer='json',
    result_serializer='json',
    accept_content=['json']
)

# --- Конфигурация Celery ---
celery_app.conf.update(
    task_track_started=True, # Отслеживать старт задачи
    timezone = 'UTC', # Устанавливаем таймзону
     broker_connection_retry_on_startup=True, # Опционально
)

# --- Расписание Beat (пустое, так как send_due_reminders удалена) ---
 celery_app.conf.beat_schedule = {}

# --------------------------------------------------------------------------
# ЗАДАЧА ГЕНЕРАЦИИ АЧИВКИ (для Фазы 3)
# --------------------------------------------------------------------------

# Внутренняя асинхронная логика для задачи
async def _run_generate_achievement_logic(
    task_instance, # Экземпляр задачи Celery (из bind=True)
    user_id: str,
    achievement_code: str,
    theme: str | None = "A generic positive achievement"
    ) -> str:
    """Содержит основную асинхронную логику задачи генерации ачивки."""
    task_id = task_instance.request.id
    log.info(f">>> [_run_achv_logic START] Task ID: {task_id} for user '{user_id}', code '{achievement_code}', theme: '{theme}'")
    
    gcs_client: Optional[storage.Client] = None
    achievement_status = "FAILED_PREPARATION" # Начальный статус

    try:
        # Инициализация клиентов
        llm = LLMClient() # LLMClient должен быть доступен и корректно инициализировать провайдера
        try:
            if settings.GCS_BUCKET_NAME: # Создаем GCS клиент, только если бакет настроен
                gcs_client = storage.Client() # Аутентификация через GOOGLE_APPLICATION_CREDENTIALS
                log.debug(f"[_run_achv_logic {task_id}] GCS Client initialized for bucket: {settings.GCS_BUCKET_NAME}")
            else:
                log.warning(f"[_run_achv_logic {task_id}] GCS_BUCKET_NAME not configured. Icon upload will be skipped.")
        except Exception as e_gcs_init:
             log.exception(f"[_run_achv_logic {task_id}] Failed to initialize GCS client: {e_gcs_init}")
             # Не прерываем задачу, просто не будет загрузки иконки

        async with async_session_context() as session:
            log.debug(f"[_run_achv_logic {task_id}] DB Session created.")

            # 1. Найти правило ачивки (AchievementRule)
            stmt_rule = sa.select(AchievementRule).where(AchievementRule.code == achievement_code)
            rule = (await session.execute(stmt_rule)).scalar_one_or_none()
            if not rule:
                 log.error(f"[_run_achv_logic {task_id}] AchievementRule '{achievement_code}' not found. Ignoring task.")
                 raise Ignore() # Задача не должна повторяться, если нет правила

            # 2. Найти или создать запись Achievement (со статусом "PENDING"?)
            stmt_ach = sa.select(Achievement).where(Achievement.user_id == user_id, Achievement.code == achievement_code)
            achievement = (await session.execute(stmt_ach)).scalar_one_or_none()

            if not achievement:
                 # Если AchievementsService должен был создать запись, а ее нет - это ошибка
                 log.error(f"[_run_achv_logic {task_id}] Achievement record for user '{user_id}', code '{achievement_code}' not found (should have been created by service). Ignoring task.")
                 raise Ignore()
            
            # Проверка, не сгенерирована ли уже (на случай повторного запуска)
            if achievement.badge_png_url and achievement.title != "PENDING_GENERATION" and achievement.title is not None:
                 log.warning(f"[_run_achv_logic {task_id}] Achievement user '{user_id}', code '{achievement_code}' already seems complete. Skipping generation.")
                 return f"ALREADY_COMPLETED:{achievement.id}"
            
            achievement_status = "PROCESSING"

            # 3. Генерация Названия через Gemini (LLMClient)
            log.info(f"[_run_achv_logic {task_id}] Generating achievement title...")
            # Используем более конкретный контекст для генерации
            name_gen_context = theme or rule.generation_context or rule.description or rule.title or "a cool achievement"
            name_style_id = "default_game_style" # Пример
            name_tone_hint = "Exciting, Short, Memorable"
            name_style_examples = "1. First Blood!\n2. Level Up!\n3. Treasure Hunter"
            
            generated_names = await llm.generate_achievement_name(
                context=name_gen_context,
                style_id=name_style_id,
                tone_hint=name_tone_hint,
                style_examples=name_style_examples
            )
            achievement_title = generated_names[0] if generated_names else "New Achievement!" # Берем первый или дефолт
            log.info(f"[_run_achv_logic {task_id}] Title generated: '{achievement_title}'")

            # 4. Генерация Иконки (PNG) через Imagen (LLMClient)
            log.info(f"[_run_achv_logic {task_id}] Generating achievement icon...")
            icon_gen_context = theme or rule.title or achievement_title
            icon_style_id = "flat_badge_icon" # Пример
            icon_style_keywords = "minimalist achievement badge, flat design, simple shapes, bold outline, vibrant solid colors"
            icon_palette_hint = "gold, blue, white"
            icon_shape_hint = "circle"
            icon_png_bytes: bytes | None = None
            try:
                 icon_png_bytes = await llm.generate_achievement_icon(
                      context=icon_gen_context,
                      style_id=icon_style_id,
                      style_keywords=icon_style_keywords,
                      palette_hint=icon_palette_hint,
                      shape_hint=icon_shape_hint
                 )
                 if not icon_png_bytes:
                      log.warning(f"[_run_achv_logic {task_id}] Imagen returned no icon bytes.")
                 else:
                      log.info(f"[_run_achv_logic {task_id}] Icon PNG generated ({len(icon_png_bytes)} bytes).")
            except NotImplementedError: # Если метод не реализован в провайдере
                 log.warning(f"[_run_achv_logic {task_id}] Icon generation (generate_achievement_icon) not implemented in LLM provider.")
            except Exception as e_img:
                 log.exception(f"[_run_achv_logic {task_id}] Failed to generate icon: {e_img}")
                 # Не прерываем, просто не будет иконки

            # 5. Загрузка Иконки в GCS (если есть иконка и клиент GCS)
            badge_png_url: str | None = None
            if icon_png_bytes and gcs_client and settings.GCS_BUCKET_NAME:
                log.info(f"[_run_achv_logic {task_id}] Uploading icon to GCS bucket '{settings.GCS_BUCKET_NAME}'...")
                try:
                    bucket = gcs_client.bucket(settings.GCS_BUCKET_NAME)
                    blob_name = f"achievements_badges/{user_id}/{achievement_code}_{task_id[:8]}.png"
                    blob = bucket.blob(blob_name)
                    
                    loop = asyncio.get_running_loop()
                    await loop.run_in_executor(
                        None, # Default ThreadPoolExecutor
                        lambda: blob.upload_from_string(icon_png_bytes, content_type='image/png')
                    )
                    # Делаем объект публично читаемым (настройте ACL бакета соответствующим образом)
                    await loop.run_in_executor(None, blob.make_public)
                    badge_png_url = blob.public_url
                    log.info(f"[_run_achv_logic {task_id}] Icon uploaded to GCS: {badge_png_url}")
                except GoogleAPICallError as e_gcs:
                    log.exception(f"[_run_achv_logic {task_id}] GCS API Error during icon upload: {e_gcs}")
                except Exception as e_gcs_other:
                     log.exception(f"[_run_achv_logic {task_id}] Unexpected error uploading icon to GCS: {e_gcs_other}")
            elif icon_png_bytes:
                 log.warning(f"[_run_achv_logic {task_id}] Icon generated, but GCS client or bucket name not configured. Skipping upload.")

            # 6. Обновление Записи Achievement в БД
            log.info(f"[_run_achv_logic {task_id}] Updating achievement record in DB...")
            achievement.title = achievement_title
            achievement.badge_png_url = badge_png_url # Используем правильное имя поля
            # achievement.status = "COMPLETED" # Если есть поле статуса
            achievement.updated_at = func.now() # Используем sqlalchemy.sql.func

            session.add(achievement)
            await session.commit() # Коммитим изменения
            log.info(f"[_run_achv_logic {task_id}] Achievement record id={achievement.id} for user '{user_id}' updated successfully.")
            achievement_status = "COMPLETED"

    except Ignore:
        log.warning(f"[_run_achv_logic {task_id}] Task ignored as per business logic.")
        achievement_status = "IGNORED"
    except Exception as exc:
        log.exception(f"[_run_achv_logic {task_id}] Unhandled exception in async logic: {exc}")
        # Позволяем Celery обработать retry, перебрасывая исключение
        raise exc
    finally:
        log.debug(f"[_run_achv_logic {task_id}] Async logic finished with status: {achievement_status}")

    return f"{achievement_status}:{achievement_code}:{user_id}"

# Основная задача Celery (async def)
@celery_app.task(
    name="app.workers.tasks.generate_achievement_task",
    bind=True,
    autoretry_for=(Exception,), # Повторять при любых исключениях
    retry_kwargs={'max_retries': 3}, # Максимум 3 повтора
    retry_backoff=True, # Экспоненциальная задержка
    retry_backoff_max=300, # Максимальная задержка 5 минут
    retry_jitter=True # Случайный фактор в задержке
)
async def generate_achievement_task(
    self, # Экземпляр задачи (self)
    user_id: str,
    achievement_code: str,
    theme: str | None = "A generic positive achievement"
) -> str:
    """
    Асинхронная Celery задача для полной генерации ачивки.
    Обертка для _run_generate_achievement_logic.
    """
    return await _run_generate_achievement_logic(self, user_id, achievement_code, theme)

# --- Экспорты ---
__all__ = ["celery_app", "generate_achievement_task"] # Добавляем новую задачу в экспорт
