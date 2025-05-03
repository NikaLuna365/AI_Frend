# /app/app/workers/tasks.py (Проверенная версия для MVP)

from __future__ import annotations
import logging

# --- Импортируем Celery и создаем приложение ---
from celery import Celery
# --- УБЕДИМСЯ, что импорт settings ЕСТЬ, если он нужен для конфигурации ---
# --- Хотя URL брокера/бэкенда берутся из settings ниже ---
from app.config import settings

log = logging.getLogger(__name__)

# --- ВАЖНО: Определение celery_app ---
# Убедимся, что оно присутствует и использует правильные настройки
celery_app = Celery(
    "ai-friend", # Имя приложения Celery
    broker=settings.CELERY_BROKER_URL, # URL брокера из настроек
    backend=settings.CELERY_RESULT_BACKEND, # URL бэкенда результатов из настроек
    include=['app.workers.tasks'], # Опционально: список модулей с задачами (пока пустой)
    # Явно указываем сериализаторы
    task_serializer='json',
    result_serializer='json',
    accept_content=['json']
)
# --------------------------------------

# --- Конфигурация (опционально, можно задать и при создании) ---
celery_app.conf.update(
    task_track_started=True, # Отслеживать старт задачи
    # result_expires=3600, # Время хранения результата (в секундах)
    timezone = 'UTC', # Устанавливаем таймзону
)

# --- Расписание Beat (Закомментировано для MVP) ---
# celery_app.conf.beat_schedule = {}

# --- Определения Задач (@celery_app.task) ---
# --- ПОКА ЗАДАЧ НЕТ ДЛЯ MVP ---
# @celery_app.task(name="app.workers.tasks.some_future_task", bind=True)
# async def some_future_task(self, ...):
#     pass
# --------------------------------------------

# --- Экспортируем приложение Celery ---
__all__ = ["celery_app"]
