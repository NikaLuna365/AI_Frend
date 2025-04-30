# /app/app/workers/tasks.py - Финальная версия с asyncio.run()

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
# Импортируем нужные типы
from typing import List, Sequence, Coroutine, Any

# Импорты Celery
from celery import Celery
from celery.schedules import crontab
from celery.utils.log import get_task_logger # Используем логгер Celery

# Импорты проекта
from app.config import settings
from app.core.reminders.service import RemindersService
from app.db.base import async_session_context
# Модель для типизации
from app.core.reminders.models import Reminder


# --- Получаем стандартный логгер Celery для задач ---
# Он интегрируется с настройками логирования Celery (--loglevel)
log = get_task_logger(__name__)

# --- Инициализация Celery ---
celery_app = Celery(
    "ai-friend",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    task_serializer='json',
    result_serializer='json',
    accept_content=['json']
)

# --- Расписание Celery Beat ---
celery_app.conf.beat_schedule = {
    'send-due-reminders-every-minute': {
        'task': 'app.workers.tasks.send_due_reminders_task', # Полный путь
        'schedule': 60.0, # Каждые 60 секунд
    },
}
celery_app.conf.timezone = 'UTC'

# --------------------------------------------------------------------------
# Внутренняя асинхронная функция с основной логикой
# --------------------------------------------------------------------------
async def _run_send_due_reminders_logic(task_id: str | None) -> str:
    """Содержит основную асинхронную логику задачи."""
    log.info(">>> [_run_logic START] Task ID: %s", task_id)
    reminders_sent_count = 0
    reminders_error_count = 0
    processed_ids = []
    final_return_value = "Logic finished with unknown status."

    try:
        log.debug("[Logic %s] Entering async_session_context...", task_id)
        async with async_session_context() as session:
            log.debug("[Logic %s] Session created: %s", task_id, id(session))
            svc = RemindersService(session)
            log.debug("[Logic %s] RemindersService initialized.", task_id)

            log.debug("[Logic %s] Calling await svc.list_due_and_unsent()...", task_id)
            due_reminders: Sequence[Reminder] = await svc.list_due_and_unsent()
            log.info(
                "[Logic %s] list_due_and_unsent returned %d reminders.",
                task_id, len(due_reminders)
            )

            if not due_reminders:
                final_return_value = "No due reminders found."
                log.info("[Logic %s] %s", task_id, final_return_value)
                return final_return_value # Возврат строки

            log.info("[Logic %s] Processing %d reminders...", task_id, len(due_reminders))
            tasks_to_run = [] # Список для параллельного запуска (если решим использовать)

            for reminder in due_reminders:
                log.debug("[Logic %s] Processing reminder ID: %d", task_id, reminder.id)
                processed_ids.append(reminder.id)
                try:
                    # --- Логика отправки уведомления ---
                    log.debug("[Logic %s][Rem %d] Simulating notification send...", task_id, reminder.id)
                    await asyncio.sleep(0.05) # Имитация IO
                    log.debug("[Logic %s][Rem %d] Notification simulation done.", task_id, reminder.id)
                    # ------------------------------------

                    # --- Пометка об отправке ---
                    log.debug("[Logic %s][Rem %d] Calling await svc.mark_sent()...", task_id, reminder.id)
                    await svc.mark_sent(reminder.id)
                    log.info("[Logic %s][Rem %d] Reminder marked as sent.", task_id, reminder.id)
                    reminders_sent_count += 1

                except Exception as e_inner:
                    reminders_error_count += 1
                    log.exception(
                        "[Logic %s][Rem %d] Error processing specific reminder: %s",
                        task_id, reminder.id, e_inner
                    )
                    # Не прерываем цикл из-за ошибки одного напоминания

            final_return_value = (
                f"Processing finished. Processed IDs: {processed_ids}. "
                f"Sent: {reminders_sent_count}, Errors: {reminders_error_count}"
            )
        log.debug("[Logic %s] Exited async_session_context.", task_id)

    except Exception as e_outer:
        log.exception(
            "[Logic %s] CRITICAL error during async logic execution: %s",
            task_id, e_outer
        )
        final_return_value = f"Task logic failed with critical error: {type(e_outer).__name__}"
        # Перебрасываем исключение, чтобы задача стала FAILED
        # Это также поможет увидеть ошибку в стандартных инструментах мониторинга Celery
        raise e_outer

    log.info("[Logic %s] <<< LOGIC END >>> Returning value: %r", task_id, final_return_value)
    # Убедимся, что возвращаем строку
    return str(final_return_value)

# --------------------------------------------------------------------------
# Основная задача Celery (синхронная обертка)
# --------------------------------------------------------------------------
@celery_app.task(name="app.workers.tasks.send_due_reminders_task", bind=True)
def send_due_reminders_task(self) -> str:
    """
    Синхронная обертка для Celery Task.
    Запускает асинхронную логику _run_send_due_reminders_logic с помощью asyncio.run().
    """
    task_id = self.request.id
    log.info(">>> [TASK WRAPPER START] ID: %s. Calling asyncio.run()...", task_id)
    result_str = "Wrapper finished with unknown state."
    try:
        # --- ЗАПУСК АСИНХРОННОЙ ЛОГИКИ ---
        result_str = asyncio.run(_run_send_due_reminders_logic(task_id))
        # --------------------------------
        log.info(">>> [TASK WRAPPER END] ID: %s. asyncio.run() completed.", task_id)
        # Возвращаем результат асинхронной функции (он должен быть строкой)
        return result_str
    except Exception as e:
        # Логируем ошибку, если сам asyncio.run() или что-то вокруг него падает
        log.exception(">>> [TASK WRAPPER ERROR] ID: %s. Exception during asyncio.run(): %s", task_id, e)
        # Перебрасываем исключение, чтобы Celery зарегистрировал FAILED статус
        raise

# --- Экспорты ---
__all__ = ["celery_app", "send_due_reminders_task"]
