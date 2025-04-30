# /app/workers/tasks.py - ПОЛНАЯ ПРОВЕРЕННАЯ ВЕРСИЯ С ОТЛАДКОЙ

from __future__ import annotations

import asyncio
import logging # Импортируем logging

# Импортируем Celery и нужные утилиты
from celery import Celery
from celery.schedules import crontab

# Импортируем зависимости проекта
from app.config import settings
from app.core.reminders.service import RemindersService # Асинхронный сервис
from app.db.base import async_session_context # Асинхронный контекст сессии

# --- Получаем стандартный логгер ---
log = logging.getLogger(__name__)

# --- Инициализируем приложение Celery ДО его использования ---
celery_app = Celery(
    "ai-friend",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    # Явно указываем сериализаторы для надежности
    task_serializer='json',
    result_serializer='json',
    accept_content=['json']
)

# --- Настраиваем расписание Celery Beat ---
celery_app.conf.beat_schedule = {
    'send-due-reminders-every-minute': {
        'task': 'app.workers.tasks.send_due_reminders_task', # Полный путь к задаче
        'schedule': 60.0, # Каждые 60 секунд
    },
}
celery_app.conf.timezone = 'UTC' # Указываем таймзону

# ───────────────────────────── Задача Celery ────────────────────────────────────

@celery_app.task(name="app.workers.tasks.send_due_reminders_task", bind=True)
async def send_due_reminders_task(self) -> str: # Указываем self и тип возврата str
    """
    Асинхронная Celery-задача для отправки напоминаний.
    Включает детальное логирование для отладки проблемы с await/сериализацией.
    """
    # Логгируем старт задачи с её уникальным ID
    log.info(">>> [TASK START] ID: %s", self.request.id)
    reminders_sent_count = 0
    reminders_error_count = 0
    processed_ids = []
    # Инициализируем возвращаемое значение по умолчанию
    final_return_value: str = "Task finished with unexpected state."

    try:
        # Шаг 1: Вход в асинхронный контекст сессии
        log.debug("[TASK %s] Entering async_session_context...", self.request.id)
        async with async_session_context() as session:
            log.debug("[TASK %s] AsyncSession created: %s", self.request.id, id(session))

            # Шаг 2: Инициализация асинхронного сервиса
            svc = RemindersService(session)
            log.debug("[TASK %s] RemindersService initialized.", self.request.id)

            # Шаг 3: Вызов первого асинхронного метода сервиса
            log.debug("[TASK %s] Calling await svc.list_due_and_unsent()...", self.request.id)
            # --- ПРОВЕРКА await ---
            due_reminders = await svc.list_due_and_unsent()
            # -----------------------
            log.info(
                "[TASK %s] svc.list_due_and_unsent returned: type=%s, count=%d",
                self.request.id, type(due_reminders), len(due_reminders)
            )

            # Проверка, не вернулась ли корутина (хотя await должен был разрешить)
            if asyncio.iscoroutine(due_reminders): # Добавим явную проверку
                 log.error("[TASK %s] ERROR: list_due_and_unsent returned a coroutine!", self.request.id)
                 raise TypeError("list_due_and_unsent returned a coroutine instead of results")

            if not due_reminders:
                final_return_value = "No due reminders found."
                log.info("[TASK %s] %s", self.request.id, final_return_value)
                # Важно: Возвращаем строку, а не None или корутину
                return final_return_value # <- Корректный выход из функции

            # Шаг 4: Начало цикла обработки
            log.info("[TASK %s] Starting loop to process %d reminders...", self.request.id, len(due_reminders))
            for reminder in due_reminders:
                log.debug("[TASK %s] Processing reminder ID: %d", self.request.id, reminder.id)
                processed_ids.append(reminder.id)
                try:
                    # Шаг 4.1: Имитация асинхронной отправки
                    log.debug("[TASK %s][Rem %d] Simulating notification send (await asyncio.sleep)...", self.request.id, reminder.id)
                    # --- ПРОВЕРКА await ---
                    await asyncio.sleep(0.05)
                    # -----------------------
                    log.debug("[TASK %s][Rem %d] Notification simulation done.", self.request.id, reminder.id)

                    # Шаг 4.2: Вызов второго асинхронного метода сервиса
                    log.debug("[TASK %s][Rem %d] Calling await svc.mark_sent()...", self.request.id, reminder.id)
                    # --- ПРОВЕРКА await ---
                    mark_sent_result = await svc.mark_sent(reminder.id)
                    # -----------------------
                     # Проверка, не вернулась ли корутина
                    if asyncio.iscoroutine(mark_sent_result): # Добавим явную проверку
                        log.error("[TASK %s][Rem %d] ERROR: mark_sent returned a coroutine!", self.request.id, reminder.id)
                        # Можно либо пропустить, либо упасть - упадем для ясности
                        raise TypeError(f"mark_sent for ID {reminder.id} returned a coroutine")

                    log.info(
                        "[TASK %s][Rem %d] svc.mark_sent returned: type=%s",
                        self.request.id, reminder.id, type(mark_sent_result)
                    )
                    reminders_sent_count += 1

                except Exception as e_inner:
                    # Логируем ошибку для конкретного напоминания, но не падаем
                    reminders_error_count += 1
                    log.exception(
                        "[TASK %s][Rem %d] Error processing specific reminder: %s",
                        self.request.id, reminder.id, e_inner
                    )
                    # НЕ ДЕЛАЕМ raise e_inner

            # Шаг 5: Формирование итогового сообщения после цикла
            final_return_value = (
                f"Processing finished. Processed IDs: {processed_ids}. "
                f"Sent: {reminders_sent_count}, Errors: {reminders_error_count}"
            )
            log.info("[TASK %s] Loop finished.", self.request.id)

        # Шаг 6: Выход из контекстного менеджера сессии
        log.debug("[TASK %s] Exited async_session_context.", self.request.id)

    except Exception as e_outer:
        # Шаг 7: Обработка критической ошибки на уровне задачи
        log.exception(
            "[TASK %s] CRITICAL error during task execution: %s",
            self.request.id, e_outer
        )
        final_return_value = f"Task failed with critical error: {type(e_outer).__name__}"
        # Не перебрасываем исключение, чтобы попытаться вернуть строку
        # raise e_outer

    # Шаг 8: Финальный возврат значения из задачи
    log.info("[TASK %s] <<< TASK END >>> Returning value: %r (Type: %s)",
             self.request.id, final_return_value, type(final_return_value))
    # Убедимся, что возвращается именно строка
    if not isinstance(final_return_value, str):
        log.error("[TASK %s] FINAL RETURN VALUE IS NOT STRING! Type: %s", self.request.id, type(final_return_value))
        return "Error: Final return value was not a string." # Возвращаем строку-ошибку

    return final_return_value # Возвращаем строку

# --- Экспорты ---
__all__ = ["celery_app", "send_due_reminders_task"]
