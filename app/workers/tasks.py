# app/workers/tasks.py
from __future__ import annotations

import asyncio
import logging # Убедимся, что logging импортирован

from celery import Celery
from celery.schedules import crontab

from app.config import settings
from app.core.reminders.service import RemindersService
from app.db.base import async_session_context

# --- Получаем логгер ---
log = logging.getLogger(__name__) # Используем существующий логгер

celery_app = Celery(
    "ai-friend",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    task_serializer='json',
    result_serializer='json',
    accept_content=['json']
)

celery_app.conf.beat_schedule = {
    'send-due-reminders-every-minute': {
        'task': 'app.workers.tasks.send_due_reminders_task',
        'schedule': 60.0,
    },
}
celery_app.conf.timezone = 'UTC'

@celery_app.task(name="app.workers.tasks.send_due_reminders_task", bind=True)
async def send_due_reminders_task(self) -> str:
    log.info(">>> [TASK START] ID: %s", self.request.id) # Лог старта задачи
    reminders_sent_count = 0
    reminders_error_count = 0
    processed_ids = []
    final_return_value = "Task finished with unknown status." # Дефолтное значение

    try:
        log.debug("[TASK %s] Entering async_session_context...", self.request.id)
        async with async_session_context() as session:
            log.debug("[TASK %s] Session created: %s", self.request.id, id(session))
            svc = RemindersService(session)
            log.debug("[TASK %s] RemindersService initialized.", self.request.id)

            # --- Вызов 1: list_due_and_unsent ---
            log.debug("[TASK %s] Calling await svc.list_due_and_unsent()...", self.request.id)
            due_reminders = await svc.list_due_and_unsent()
            # ЛОГГИРУЕМ ТИП и РЕЗУЛЬТАТ
            log.info(
                "[TASK %s] list_due_and_unsent returned %d reminders. Type: %s",
                self.request.id, len(due_reminders), type(due_reminders)
            )

            if not due_reminders:
                final_return_value = "No due reminders."
                log.info("[TASK %s] %s", self.request.id, final_return_value)
                return final_return_value # <- Явный возврат строки

            log.info("[TASK %s] Processing %d reminders...", self.request.id, len(due_reminders))

            for reminder in due_reminders:
                log.debug("[TASK %s] Processing reminder ID: %d", self.request.id, reminder.id)
                processed_ids.append(reminder.id)
                try:
                    # --- Имитация отправки ---
                    log.debug("[TASK %s][Rem %d] Simulating notification send...", self.request.id, reminder.id)
                    await asyncio.sleep(0.05) # <- await есть
                    log.debug("[TASK %s][Rem %d] Notification simulation done.", self.request.id, reminder.id)

                    # --- Вызов 2: mark_sent ---
                    log.debug("[TASK %s][Rem %d] Calling await svc.mark_sent()...", self.request.id, reminder.id)
                    mark_sent_result = await svc.mark_sent(reminder.id) # <- await есть
                    # ЛОГГИРУЕМ ТИП и РЕЗУЛЬТАТ
                    log.info(
                        "[TASK %s][Rem %d] mark_sent returned. Type: %s. Result: %r",
                        self.request.id, reminder.id, type(mark_sent_result), mark_sent_result
                    )

                    reminders_sent_count += 1

                except Exception as e_inner:
                    reminders_error_count += 1
                    log.exception(
                        "[TASK %s][Rem %d] Error processing specific reminder: %s",
                        self.request.id, reminder.id, e_inner
                    )
                    # Продолжаем цикл

            # Формируем финальное сообщение после цикла
            final_return_value = (
                f"Finished processing. Processed IDs: {processed_ids}. "
                f"Sent: {reminders_sent_count}, Errors: {reminders_error_count}"
            )

        # Выход из контекстного менеджера сессии (автоматический commit/rollback)
        log.debug("[TASK %s] Exited async_session_context.", self.request.id)

    except Exception as e_outer:
        log.exception(
            "[TASK %s] CRITICAL error during task execution: %s",
            self.request.id, e_outer
        )
        # Устанавливаем значение для возврата в случае критической ошибки
        final_return_value = f"Task failed with critical error: {type(e_outer).__name__}"
        # Важно: Не перебрасываем исключение здесь, чтобы Celery попытался
        # сериализовать хотя бы 'final_return_value', а не само исключение.
        # Мы увидим ошибку FAILED в статусе задачи и полный лог выше.
        # raise e_outer # --- ВРЕМЕННО УБИРАЕМ ПЕРЕБРОС ---

    # --- Финальный возврат ---
    log.info("[TASK %s] <<< TASK END >>> Returning value: %s (Type: %s)",
             self.request.id, final_return_value, type(final_return_value))
    return final_return_value # <- Возвращаем строку

__all__ = ["celery_app", "send_due_reminders_task"]
