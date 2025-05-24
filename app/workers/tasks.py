# /app/app/workers/tasks.py (Дополненная задача ачивок с реальной GCS загрузкой)

from __future__ import annotations

import asyncio
import logging
import base64
import tempfile # Может не понадобиться, если работаем с байтами в памяти
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
# --- Клиент GCS и ошибки ---
from google.cloud import storage
from google.auth.exceptions import DefaultCredentialsError # Для отлова ошибок инициализации клиента
from google.api_core.exceptions import GoogleAPICallError
# ---------------------------
from typing import Optional, List, Sequence, Any

log = get_task_logger(__name__)

# Инициализация Celery (как в #89)
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
    timezone='UTC',
    broker_connection_retry_on_startup=True,
)
# celery_app.conf.beat_schedule = {}

# --- Внутренняя асинхронная логика для задачи ---
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
    llm = LLMClient() # Инициализируем LLM клиент

    try:
        # Инициализация GCS клиента (если настроен)
        if settings.GCS_BUCKET_NAME:
            try:
                # GOOGLE_APPLICATION_CREDENTIALS должен быть установлен в окружении контейнера
                gcs_client = storage.Client()
                log.debug(f"[_run_achv_logic {task_id}] GCS Client initialized for bucket: {settings.GCS_BUCKET_NAME}")
            except DefaultCredentialsError as e_gcs_auth:
                log.error(f"[_run_achv_logic {task_id}] GCS Auth Error: {e_gcs_auth}. Ensure GOOGLE_APPLICATION_CREDENTIALS is set and valid.")
                gcs_client = None # Не сможем загрузить
            except Exception as e_gcs_init:
                 log.exception(f"[_run_achv_logic {task_id}] Failed to initialize GCS client: {e_gcs_init}")
                 gcs_client = None # Не сможем загрузить
        else:
            log.warning(f"[_run_achv_logic {task_id}] GCS_BUCKET_NAME not configured. Icon upload will be skipped.")

        async with async_session_context() as session:
            log.debug(f"[_run_achv_logic {task_id}] DB Session created.")
            actual_theme_for_generation = theme or "a significant accomplishment"

            # Получаем/Создаем запись ачивки
            stmt_ach = sa.select(Achievement).where(Achievement.user_id == user_id, Achievement.code == achievement_code)
            achievement = (await session.execute(stmt_ach)).scalar_one_or_none()

            if not achievement:
                 log.error(f"[_run_achv_logic {task_id}] Achievement record '{achievement_code}' for user '{user_id}' not found. This should have been created by AchievementsService. Ignoring.")
                 raise Ignore()
            
            if achievement.status == "COMPLETED":
                 log.warning(f"[_run_achv_logic {task_id}] Achievement '{achievement_code}' for user '{user_id}' already COMPLETED. Skipping.")
                 return f"ALREADY_COMPLETED:{achievement.id}"

            # Устанавливаем статус PROCESSING и коммитим, чтобы было видно, что задача в работе
            achievement.status = "PROCESSING"
            if not achievement.title or achievement.title.startswith("Pending:"): # Если еще не было попытки генерации имени
                achievement.title = "Generating title..."
            session.add(achievement)
            await session.commit()
            log.info(f"[_run_achv_logic {task_id}] Achievement '{achievement.code}' status set to PROCESSING.")

            # Шаг 1: Генерация Названия
            log.info(f"[_run_achv_logic {task_id}] Generating achievement title...")
            # ... (параметры для generate_achievement_name, как в #89) ...
            name_style_id = "default_game_style"
            name_tone_hint = "Exciting, Short, Memorable"
            name_style_examples = "1. Victory!\n2. Quest Complete!\n3. Legend Born"
            generated_names = await llm.generate_achievement_name(
                context=actual_theme_for_generation, style_id=name_style_id, tone_hint=name_tone_hint, style_examples=name_style_examples
            )
            achievement_title = generated_names[0] if generated_names else f"{achievement_code.replace('_',' ').title()} Unlocked!"
            log.info(f"[_run_achv_logic {task_id}] Title generated: '{achievement_title}'")

            # Шаг 2: Генерация Иконки
            log.info(f"[_run_achv_logic {task_id}] Generating achievement icon...")
            # ... (параметры для generate_achievement_icon, как в #89) ...
            icon_style_id = "flat_badge_icon_v2"
            icon_style_keywords = "minimalist achievement badge, flat design, simple vector art, bold outline"
            icon_palette_hint = "gold, blue, white, black outline"
            icon_shape_hint = "circle"
            icon_png_bytes: bytes | None = await llm.generate_achievement_icon(
                context=actual_theme_for_generation, style_id=icon_style_id, style_keywords=icon_style_keywords,
                palette_hint=icon_palette_hint, shape_hint=icon_shape_hint
            ) # generate_achievement_icon теперь должен вызывать Imagen

            # Шаг 3: Загрузка Иконки в GCS
            badge_png_url: str | None = None
            if icon_png_bytes and gcs_client and settings.GCS_BUCKET_NAME:
                log.info(f"[_run_achv_logic {task_id}] Uploading icon to GCS bucket '{settings.GCS_BUCKET_NAME}'...")
                try:
                    bucket = gcs_client.bucket(settings.GCS_BUCKET_NAME)
                    # Уникальное имя файла для иконки
                    blob_name = f"badges/achievements/{user_id}/{achievement_code}_{task_id[:12]}.png"
                    blob = bucket.blob(blob_name)
                    
                    loop = asyncio.get_running_loop()
                    # Передаем байты напрямую
                    await loop.run_in_executor(
                        None, # Default ThreadPoolExecutor
                        lambda: blob.upload_from_string(icon_png_bytes, content_type='image/png')
                    )
                    # Устанавливаем публичный доступ (или используем Signed URL в будущем)
                    await loop.run_in_executor(None, blob.make_public)
                    badge_png_url = blob.public_url # Получаем публичный URL
                    log.info(f"[_run_achv_logic {task_id}] Icon uploaded to GCS: {badge_png_url}")
                except GoogleAPICallError as e_gcs:
                    log.exception(f"[_run_achv_logic {task_id}] GCS API Error during icon upload: {e_gcs}")
                except Exception as e_gcs_other:
                     log.exception(f"[_run_achv_logic {task_id}] Unexpected error uploading icon to GCS: {e_gcs_other}")
            elif icon_png_bytes:
                 log.warning(f"[_run_achv_logic {task_id}] Icon generated, but GCS client or bucket name not configured/initialized. Skipping upload.")
            elif not icon_png_bytes:
                log.warning(f"[_run_achv_logic {task_id}] No icon bytes were generated. Skipping GCS upload.")


            # Шаг 4: Обновление Записи Achievement в БД
            log.info(f"[_run_achv_logic {task_id}] Updating achievement record in DB with final data...")
            achievement.title = achievement_title
            achievement.badge_png_url = badge_png_url
            achievement.status = "COMPLETED"
            achievement.updated_at = func.now() # Используем sqlalchemy.sql.func
            session.add(achievement)
            await session.commit() # Финальный коммит
            log.info(f"[_run_achv_logic {task_id}] Achievement '{achievement_code}' for user '{user_id}' set to COMPLETED.")
            achievement_status = "COMPLETED"

    except Ignore:
        achievement_status = "IGNORED"; log.warning(f"[_run_achv_logic {task_id}] Task ignored.")
    except Exception as exc:
        log.exception(f"[_run_achv_logic {task_id}] Unhandled exception in async logic: {exc}")
        achievement_status = "ERROR_IN_LOGIC"
        # Попытка обновить статус ачивки на FAILED_GENERATION
        try:
            async with async_session_context() as error_session:
                stmt_ach_err = sa.select(Achievement).where(Achievement.user_id == user_id, Achievement.code == achievement_code)
                ach_to_fail = (await error_session.execute(stmt_ach_err)).scalar_one_or_none()
                if ach_to_fail and ach_to_fail.status != "COMPLETED": # Не перезаписываем уже успешную
                    ach_to_fail.status = "FAILED_GENERATION"
                    ach_to_fail.updated_at = func.now()
                    error_session.add(ach_to_fail)
                    await error_session.commit()
                    log.info(f"Marked achievement {achievement_code} for user {user_id} as FAILED_GENERATION.")
        except Exception as db_err_update:
            log.exception(f"Failed to mark achievement as FAILED_GENERATION after main error: {db_err_update}")
        raise # Перебрасываем исходное исключение для механизма retry Celery
    finally:
        log.debug(f"[_run_achv_logic {task_id}] Async logic finished with status: {achievement_status}")

    return f"{achievement_status}:{achievement.id if 'achievement' in locals() and achievement else 'N/A'}"


# Основная задача Celery (остается async def)
@celery_app.task(
    name="app.workers.tasks.generate_achievement_task",
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 3},
    retry_backoff=True, # default: 0, 1, 2, 4, 8...
    retry_backoff_max=60 * 5, # 5 минут
    retry_jitter=True
)
async def generate_achievement_task(
    self,
    user_id: str,
    achievement_code: str, # Код "зашитого" правила
    theme: str | None = "A generic positive achievement" # Тема для генерации
) -> str:
    """Асинхронная Celery задача для генерации ачивки."""
    return await _run_generate_achievement_logic(self, user_id, achievement_code, theme)

__all__ = ["celery_app", "generate_achievement_task"]
