# app/workers/tasks.py
from __future__ import annotations

import asyncio
import logging

from celery import Celery
from celery.schedules import crontab

from app.config import settings
from app.core.reminders.service import RemindersService
from app.db.base import async_session_context

log = logging.getLogger(__name__)

celery_app = Celery(
    "ai-friend",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    # --- Явно указываем настройки сериализации ---
    task_serializer='json',
    result_serializer='json',
    accept_content=['json']
    # -------------------------------------------
)

celery_app.conf.beat_schedule = {
    'send-due-reminders-every-minute': {
        'task': 'app.workers.tasks.send_due_reminders_task',
        'schedule': 60.0,
    },
}
celery_app.conf.timezone = 'UTC'

@celery_app.task(name="app.workers.tasks.send_due_reminders_task", bind=True) # Добавляем bind=True
async def send_due_reminders_task(self) -> str: # Указываем self и возвращаемый тип str
    """
    Асинхронная Celery-задача для отправки напоминаний, срок которых наступил.
    """
    log.info("Starting send_due_reminders_task (Task ID: %s)...", self.request.id) # Логгируем ID задачи
    reminders_sent_count = 0
    reminders_error_count = 0
    processed_ids = []

    try: # Оборачиваем весь код задачи в try/except для лучшего контроля
        async with async_session_context() as session:
            svc = RemindersService(session)
            due_reminders = await svc.list_due_and_unsent()

            if not due_reminders:
                log.info("No due reminders to send.")
                return "No due reminders." # Явно возвращаем строку

            log.info("Found %d due reminders to process.", len(due_reminders))

            for reminder in due_reminders:
                try:
                    processed_ids.append(reminder.id) # Собираем ID для лога
                    # --- Логика отправки уведомления ---
                    log.info(
                        "Simulating sending reminder id=%d to user %s: '%s'",
                        reminder.id, reminder.user_id, reminder.title
                    )
                    await asyncio.sleep(0.05) # Уменьшим задержку
                    # ------------------------------------
                    await svc.mark_sent(reminder.id)
                    reminders_sent_count += 1

                except Exception as e:
                    reminders_error_count += 1
                    log.exception(
                        "Error processing specific reminder id=%d for user %s: %s",
                        reminder.id, reminder.user_id, e
                    )
                    # НЕ ПЕРЕБРАСЫВАЕМ ошибку здесь, чтобы продолжить цикл

        result_message = (
            f"Finished send_due_reminders_task. Processed IDs: {processed_ids}. "
            f"Sent: {reminders_sent_count}, Errors: {reminders_error_count}"
        )
        log.info(result_message)
        return result_message # Явно возвращаем строку

    except Exception as e:
        # Ловим ЛЮБОЕ исключение на верхнем уровне задачи
        log.exception(
            "CRITICAL error in send_due_reminders_task (Task ID: %s): %s",
            self.request.id, e
        )
        # Важно: Перебрасываем исключение, чтобы Celery зарегистрировал сбой задачи,
        # но убедимся, что оно сериализуемо. Стандартные исключения обычно сериализуемы.
        # Можно обернуть в стандартное исключение Celery при необходимости.
        raise e # Celery должен сам обработать стандартные исключения
