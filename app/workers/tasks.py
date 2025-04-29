# app/workers/tasks.py
from __future__ import annotations

import asyncio
import logging

from celery import Celery
from celery.schedules import crontab # Для возможного использования crontab-расписания

from app.config import settings
# Импортируем асинхронный сервис и контекст сессии
from app.core.reminders.service import RemindersService
from app.db.base import async_session_context

log = logging.getLogger(__name__)

# Настройка Celery остается прежней
celery_app = Celery(
    "ai-friend",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    # Опционально: Настройка для лучшей интеграции с asyncio
    # event_loop='uvloop' # Если используете uvloop для производительности
)

# Настройка расписания для Celery Beat
celery_app.conf.beat_schedule = {
    'send-due-reminders-every-minute': {
        'task': 'app.workers.tasks.send_due_reminders_task', # Полный путь к задаче
        'schedule': 60.0,  # Запускать каждые 60 секунд
        # Можно использовать crontab: 'schedule': crontab(minute='*'), # Каждую минуту
    },
}
celery_app.conf.timezone = 'UTC' # Устанавливаем таймзону для Celery Beat

# ─────────────────────────────  tasks  ────────────────────────────────────

# Определяем задачу как async def
@celery_app.task(name="app.workers.tasks.send_due_reminders_task")
async def send_due_reminders_task() -> None:
    """
    Асинхронная Celery-задача для отправки напоминаний, срок которых наступил.
    Использует асинхронный контекст сессии и асинхронный RemindersService.
    """
    log.info("Starting send_due_reminders_task...")
    reminders_sent_count = 0
    reminders_error_count = 0

    # Используем асинхронный контекст сессии
    async with async_session_context() as session:
        try:
            # Создаем экземпляр сервиса с активной сессией
            svc = RemindersService(session)

            # Получаем напоминания, готовые к отправке
            due_reminders = await svc.list_due_and_unsent()

            if not due_reminders:
                log.info("No due reminders to send.")
                return # Выходим, если нет напоминаний

            log.info("Found %d due reminders to process.", len(due_reminders))

            # Группируем отправку и обновление статуса
            # (Можно использовать asyncio.gather для параллельной отправки,
            # но пока сделаем последовательно для простоты)
            for reminder in due_reminders:
                try:
                    # --- Логика отправки уведомления ---
                    # TODO: Заменить это реальной асинхронной отправкой
                    # Например:
                    # notification_client = get_notification_client() # Получаем клиент (e.g., WebPush, Email)
                    # await notification_client.send(
                    #     user_id=reminder.user_id,
                    #     title="Напоминание!",
                    #     body=reminder.title
                    # )
                    log.info(
                        "Simulating sending reminder id=%d to user %s: '%s'",
                        reminder.id, reminder.user_id, reminder.title
                    )
                    # Имитируем небольшую задержку сети/обработки
                    await asyncio.sleep(0.1)
                    # ------------------------------------

                    # Если отправка прошла успешно, помечаем как отправленное
                    await svc.mark_sent(reminder.id)
                    reminders_sent_count += 1
                    log.info("Successfully processed and marked reminder id=%d as sent.", reminder.id)

                except Exception as e:
                    # Логируем ошибку при отправке/обновлении конкретного напоминания,
                    # но продолжаем обрабатывать остальные
                    reminders_error_count += 1
                    log.exception(
                        "Error processing reminder id=%d for user %s: %s",
                        reminder.id, reminder.user_id, e
                    )
                    # Важно: НЕ ДЕЛАЕМ rollback всей транзакции здесь,
                    # чтобы успешно отправленные напоминания остались помеченными.
                    # Откат произойдет автоматически в контекстном менеджере,
                    # если возникнет НЕПЕРЕХВАЧЕННОЕ исключение выше.

            # Коммит транзакции происходит автоматически при выходе из async_session_context
            # если не было неперехваченных исключений.

        except Exception as e:
            # Логируем ошибку на уровне всей задачи (например, ошибка подключения к БД)
            log.exception("Critical error in send_due_reminders_task: %s", e)
            # Откат транзакции произойдет автоматически в async_session_context

    log.info(
        "Finished send_due_reminders_task. Sent: %d, Errors: %d",
        reminders_sent_count, reminders_error_count
    )

# Опционально: можно добавить другие задачи

# Убедимся, что celery_app импортируется правильно
# Например, если celery worker запускается как `celery -A app.workers.tasks worker ...`
# то этот файл должен быть доступен для импорта.

__all__ = ["celery_app", "send_due_reminders_task"]
