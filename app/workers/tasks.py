# /app/app/workers/tasks.py (Добавляем generate_achievement_task)

from __future__ import annotations

import asyncio
import logging
import base64 # Для работы с изображением из Imagen
import tempfile # Для временного сохранения PNG
import os

from celery import Celery
from celery.exceptions import Ignore # Для обработки известных ошибок без retry
from celery.utils.log import get_task_logger

# --- Импорты проекта ---
from app.config import settings
# Сервис Ачивок (для обновления статуса/данных)
from app.core.achievements.service import AchievementsService
# Модели (для работы с БД напрямую или через сервис)
from app.core.achievements.models import Achievement, AchievementRule
# LLM Клиент (для генерации названия и ИКОНКИ через Imagen)
from app.core.llm.client import LLMClient
# Контекст БД
from app.db.base import async_session_context, AsyncSession
# Клиент GCS
from google.cloud import storage
from google.api_core.exceptions import GoogleAPICallError

log = get_task_logger(__name__)

# --- Инициализация Celery (оставляем как есть) ---
celery_app = Celery("ai-friend", broker=..., backend=..., ...)
# ... (конфигурация celery_app) ...

# --------------------------------------------------------------------------
# НОВАЯ ЗАДАЧА: Генерация Ачивки
# --------------------------------------------------------------------------
# Настройки Retry: Повторить 3 раза с задержкой 60, 120, 240 секунд
# Это поможет при временных сбоях API Google или сети.
@celery_app.task(
    name="app.workers.tasks.generate_achievement_task",
    bind=True,
    autoretry_for=(Exception,), # Повторять при ЛЮБОМ исключении
    retry_kwargs={'max_retries': 3},
    retry_backoff=True, # Экспоненциальная задержка (5, 10, 20 сек по умолчанию)
    retry_backoff_max=300, # Максимальная задержка 5 минут
    retry_jitter=True # Случайный фактор в задержке
)
async def generate_achievement_task(
    self, # Экземпляр задачи (из bind=True)
    user_id: str,
    achievement_code: str,
    theme: str | None = "A generic positive achievement" # Тема/контекст для генерации
    ) -> str: # Возвращаем статус или ID ачивки
    """
    Асинхронная Celery задача для полной генерации ачивки:
    1. Генерирует название через LLM (Gemini).
    2. Генерирует иконку через Vertex AI Imagen.
    3. Загружает иконку в Google Cloud Storage.
    4. Обновляет запись Achievement в базе данных.
    """
    task_id = self.request.id
    log.info(f"[AchvTask {task_id}] Starting generation for user '{user_id}', code '{achievement_code}', theme '{theme}'")

    gcs_client: storage.Client | None = None
    achievement_status = "FAILED" # Статус по умолчанию

    try:
        # --- Шаг 0: Получаем LLM клиент и сессию БД ---
        # LLMClient должен быть доступен (инициализирован в фабрике)
        llm = LLMClient()
        # GCS клиент - создаем здесь или через DI? Проще создать здесь.
        try:
            gcs_client = storage.Client() # Аутентификация через GOOGLE_APPLICATION_CREDENTIALS
            log.debug(f"[AchvTask {task_id}] GCS Client initialized.")
        except Exception as e_gcs_init:
             log.exception(f"[AchvTask {task_id}] Failed to initialize GCS client: {e_gcs_init}")
             raise # Критическая ошибка, повторяем задачу

        async with async_session_context() as session:
            ach_service = AchievementsService(db_session=session, llm_client=llm)

            # Находим правило ачивки (если оно есть в БД)
            # rule = await ach_service._get_rule(achievement_code) # Или напрямую через сессию
            stmt_rule = sa.select(AchievementRule).where(AchievementRule.code == achievement_code)
            rule = (await session.execute(stmt_rule)).scalar_one_or_none()
            if not rule:
                 log.error(f"[AchvTask {task_id}] AchievementRule '{achievement_code}' not found in DB. Ignoring task.")
                 raise Ignore() # Не повторять задачу, если правила нет

            # Находим существующую запись Achievement (должна быть создана со статусом PENDING?)
            # Либо создаем ее здесь, если check_and_award этого не делает.
            # Предположим, check_and_award создает запись с PENDING статусом.
            stmt_ach = sa.select(Achievement).where(Achievement.user_id == user_id, Achievement.code == achievement_code)
            achievement = (await session.execute(stmt_ach)).scalar_one_or_none()

            if not achievement:
                 log.error(f"[AchvTask {task_id}] Achievement record for user '{user_id}', code '{achievement_code}' not found. Ignoring task.")
                 raise Ignore() # Не повторять

            if achievement.badge_png_url and achievement.title != "PENDING": # Проверяем, не сгенерировано ли уже
                 log.warning(f"[AchvTask {task_id}] Achievement user '{user_id}', code '{achievement_code}' already generated. Skipping.")
                 return f"ALREADY_GENERATED:{achievement.id}"

            # --- Шаг 1: Генерация Названия через Gemini ---
            log.info(f"[AchvTask {task_id}] Generating title...")
            # TODO: Определить tone_hint и style_examples (можно из правила или дефолтные)
            tone_hint = "Playful, Positive, Encouraging"
            style_examples = "1. Welcome Aboard!\n2. Milestone Reached\n3. First Step!"
            gen_names = await llm.generate_achievement_name(
                context=theme or rule.generation_context or rule.description or rule.title, # Используем доступный контекст
                style_id="general", # Пока один стиль
                tone_hint=tone_hint,
                style_examples=style_examples
            )
            achievement_title = gen_names[0] # Берем первый вариант
            log.info(f"[AchvTask {task_id}] Title generated: '{achievement_title}'")

            # --- Шаг 2: Генерация Иконки через Imagen (Vertex AI) ---
            log.info(f"[AchvTask {task_id}] Generating icon via Imagen...")
            # TODO: Определить параметры стиля, палитры, формы (из правила или дефолтные)
            style_id = "flat_cartoon"
            style_keywords = "flat design, simple shapes, bold outline, vibrant solid colors, no gradients"
            palette_hint = "blue, yellow, white" # Пример
            shape_hint = "circle"
            icon_prompt = theme or rule.title # Используем тему или название как промпт для иконки

            # Вызываем метод клиента, который должен обращаться к Imagen
            # (Предполагаем, что LLMClient имеет метод generate_achievement_icon)
            try:
                 # Возвращает байты PNG изображения
                 icon_png_bytes = await llm.generate_achievement_icon(
                      context=icon_prompt,
                      style_id=style_id,
                      style_keywords=style_keywords,
                      palette_hint=palette_hint,
                      shape_hint=shape_hint
                 )
                 if not icon_png_bytes:
                      raise ValueError("Imagen returned empty bytes for the icon.")
                 log.info(f"[AchvTask {task_id}] Icon PNG generated ({len(icon_png_bytes)} bytes).")
            except NotImplementedError:
                 log.warning(f"[AchvTask {task_id}] Icon generation not implemented in provider. Skipping icon.")
                 icon_png_bytes = None
            except Exception as e_img:
                 log.exception(f"[AchvTask {task_id}] Failed to generate icon via Imagen: {e_img}")
                 icon_png_bytes = None # Продолжаем без иконки при ошибке генерации

            # --- Шаг 3: Загрузка Иконки в GCS (если сгенерирована) ---
            badge_png_url = None
            if icon_png_bytes and gcs_client:
                log.info(f"[AchvTask {task_id}] Uploading icon to GCS bucket '{settings.GCS_BUCKET_NAME}'...")
                bucket = gcs_client.bucket(settings.GCS_BUCKET_NAME)
                # Формируем путь/имя файла в бакете
                blob_name = f"badges/{user_id}/{achievement_code}_{task_id[:8]}.png"
                blob = bucket.blob(blob_name)
                try:
                    # Загружаем из байтов
                    # Используем asyncio для неблокирующей загрузки
                    loop = asyncio.get_running_loop()
                    await loop.run_in_executor(
                        None, # Используем дефолтный executor
                        lambda: blob.upload_from_string(icon_png_bytes, content_type='image/png')
                    )
                    # Делаем файл публично читаемым (если нужно, зависит от настроек бакета)
                    # await loop.run_in_executor(None, blob.make_public)
                    badge_png_url = blob.public_url # Получаем URL
                    log.info(f"[AchvTask {task_id}] Icon uploaded to GCS: {badge_png_url}")
                except GoogleAPICallError as e_gcs:
                    log.exception(f"[AchvTask {task_id}] Failed to upload icon to GCS: {e_gcs}")
                    # Продолжаем без URL иконки
                except Exception as e_gcs_other: # Ловим другие возможные ошибки
                     log.exception(f"[AchvTask {task_id}] Unexpected error uploading icon to GCS: {e_gcs_other}")


            # --- Шаг 4: Обновление Записи Achievement в БД ---
            log.info(f"[AchvTask {task_id}] Updating achievement record in DB...")
            achievement.title = achievement_title
            achievement.badge_png_url = badge_png_url # Сохраняем URL PNG
            # achievement.status = "COMPLETED" # Если есть поле статуса
            achievement.updated_at = func.now() # Обновляем время (хотя onupdate должен сработать)

            session.add(achievement)
            await session.commit() # Коммитим изменения для этой ачивки
            log.info(f"[AchvTask {task_id}] Achievement record id={achievement.id} updated successfully.")
            achievement_status = "COMPLETED"

    except Ignore:
        # Задача игнорируется (например, не найдено правило/запись)
        log.warning(f"[AchvTask {task_id}] Task is being ignored.")
        achievement_status = "IGNORED"
    except Exception as exc:
        # Ловим ЛЮБОЕ необработанное исключение на уровне задачи
        log.exception(f"[AchvTask {task_id}] Unhandled exception in task: {exc}")
        # Помечаем как FAILED и позволяем Celery выполнить retry согласно настройкам
        # Можно добавить кастомную логику перед retry, если нужно
        # self.update_state(state='RETRY', meta={'exc_type': type(exc).__name__, 'exc_message': str(exc)})
        raise # Перебрасываем исключение для механизма retry Celery

    finally:
        # Очистка (если создавали временные файлы)
        log.debug(f"[AchvTask {task_id}] Task finished with status: {achievement_status}")
        # Здесь НЕ нужно вызывать engine.dispose(), Celery управляет соединениями иначе

    return f"{achievement_status}:{achievement_code}:{user_id}" # Возвращаем статус

# --- Экспорты ---
__all__ = ["celery_app", "generate_achievement_task"]
