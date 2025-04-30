# app/workers/tasks.py
from __future__ import annotations

import asyncio
import logging

# --- СНАЧАЛА импортируем Celery и создаем приложение ---
from celery import Celery
from celery.schedules import crontab

from app.config import settings
from app.core.reminders.service import RemindersService
from app.db.base import async_session_context

log = logging.getLogger(__name__)

# --- ОПРЕДЕЛЯЕМ celery_app ЗДЕСЬ, ДО ИСПОЛЬЗОВАНИЯ ---
celery_app = Celery(
    "ai-friend",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    task_serializer='json',
    result_serializer='json',
    accept_content=['json']
)

# Настройка расписания
celery_app.conf.beat_schedule = {
    'send-due-reminders-every-minute': {
        'task': 'app.workers.tasks.send_due_reminders_task', # Полный путь
        'schedule': 60.0,
    },
}
celery_app.conf.timezone = 'UTC'

# ─────────────────────────────  tasks  ────────────────────────────────────

# --- ТЕПЕРЬ используем celery_app в декораторе ---
# Используем ДИАГНОСТИЧЕСКУЮ ВЕРСИЮ задачи для проверки
@celery_app.task(name="app.workers.tasks.send_due_reminders_task", bind=True)
async def send_due_reminders_task(self) -> str:
    log.info("Starting DIAGNOSTIC send_due_reminders_task (Task ID: %s)...", self.request.id)
    result_message = "Task started (diagnostic)."
    try:
        async with async_session_context() as session:
            log.info("Session opened successfully.")
            svc = RemindersService(session)
            log.info("Calling list_due_and_unsent...")
            due_reminders = await svc.list_due_and_unsent()
            log.info("list_due_and_unsent returned %d reminders.", len(due_reminders))
            result_message = f"Task completed after list_due_and_unsent. Found {len(due_reminders)} reminders."

        log.info(result_message)
        return result_message

    except Exception as e:
        log.exception(
            "CRITICAL error in DIAGNOSTIC send_due_reminders_task (Task ID: %s): %s",
            self.request.id, e
        )
        raise e

# --- Убедимся, что экспорты правильные ---
__all__ = ["celery_app", "send_due_reminders_task"]
