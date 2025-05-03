# /app/app/workers/tasks.py (Версия с engine.dispose())

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import List, Sequence, Coroutine, Any

from celery import Celery
from celery.schedules import crontab
from celery.utils.log import get_task_logger

from app.config import settings
from app.core.reminders.service import RemindersService
# --- ИМПОРТИРУЕМ engine и async_session_context ---
from app.db.base import async_session_context, engine # <-- Добавили engine
# ---------------------------------------------------
from app.core.reminders.models import Reminder


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
        'task': 'app.workers.tasks.send_due_reminders_task',
        'schedule': 60.0,
    },
}
celery_app.conf.timezone = 'UTC'

# --------------------------------------------------------------------------
# Внутренняя асинхронная функция с основной логикой
# --------------------------------------------------------------------------
async def _run_send_due_reminders_logic(task_id: str | None) -> str:
    """Содержит основную асинхронную логику задачи."""
    log.info(">>> [_run_logic START] Task ID: %s", task_id)
    # ... (весь остальной код этой функции остается БЕЗ ИЗМЕНЕНИЙ, как в ответе #49) ...
    reminders_sent_count = 0
    reminders_error_count = 0
    processed_ids = []
    final_return_value = "Logic finished with unknown status."

    try:
        log.debug("[Logic %s] Entering async_session_context...", task_id)
        async with async_session_context() as session:
            # ... (код создания сервиса, вызова list_due_and_unsent) ...
             due_reminders: Sequence[Reminder] = await svc.list_due_and_unsent()
             # ... (логирование) ...
             if not due_reminders:
                  final_return_value = "No due reminders found."
                  # ...
                  return final_return_value

             # ... (логирование) ...
             for reminder in due_reminders:
                 processed_ids.append(reminder.id)
                 try:
                     # ... (логика отправки + await asyncio.sleep()) ...
                     await svc.mark_sent(reminder.id) # <- await есть
                     # ... (логирование) ...
                     reminders_sent_count += 1
                 except Exception as e_inner:
                     reminders_error_count += 1
                     log.exception(...) # Логируем ошибку для напоминания
                     # Не прерываем цикл

             final_return_value = (
                 f"Processing finished. Processed IDs: {processed_ids}. "
                 f"Sent: {reminders_sent_count}, Errors: {reminders_error_count}"
             )
        log.debug("[Logic %s] Exited async_session_context.", task_id)

    except Exception as e_outer:
        log.exception(...)
        final_return_value = f"Task logic failed with critical error: {type(e_outer).__name__}"
        # Перебрасываем ошибку, чтобы задача была FAILED
        raise e_outer # <-- Возвращаем raise для статуса FAILED

    log.info("[Logic %s] <<< LOGIC END >>> Returning value: %r", task_id, final_return_value)
    return str(final_return_value)


# --------------------------------------------------------------------------
# Основная задача Celery (синхронная обертка)
# --------------------------------------------------------------------------
@celery_app.task(name="app.workers.tasks.send_due_reminders_task", bind=True)
def send_due_reminders_task(self) -> str:
    """
    Синхронная обертка для Celery Task.
    Запускает асинхронную логику _run_send_due_reminders_logic с помощью asyncio.run()
    и очищает пул соединений SQLAlchemy после выполнения.
    """
    task_id = self.request.id
    log.info(">>> [TASK WRAPPER START] ID: %s. Calling asyncio.run()...", task_id)
    result_str = "Task failed before completion."
    try:
        # Запускаем асинхронную логику
        result_str = asyncio.run(_run_send_due_reminders_logic(task_id))
        log.info(">>> [TASK WRAPPER END] ID: %s. asyncio.run() completed.", task_id)
        return result_str
    except Exception as e:
        log.exception(">>> [TASK WRAPPER ERROR] ID: %s. Exception during asyncio.run(): %s", task_id, e)
        # --- ВАЖНО: Перебрасываем исключение ПОСЛЕ finally ---
        raise # Гарантирует статус FAILED в Celery
    finally:
        # --- ЯВНО ОЧИЩАЕМ ПУЛ СОЕДИНЕНИЙ ---
        if engine:
            # Проверяем, что движок асинхронный перед вызовом dispose
            if hasattr(engine, "dispose") and asyncio.iscoroutinefunction(engine.dispose):
                try:
                    # Используем asyncio.run для вызова async dispose
                    log.info(">>> [TASK WRAPPER FINALLY] ID: %s. Disposing DB engine pool...", task_id)
                    asyncio.run(engine.dispose())
                    log.info(">>> [TASK WRAPPER FINALLY] ID: %s. DB engine pool disposed.", task_id)
                except RuntimeError as loop_err:
                     # Может возникнуть ошибка "Cannot run the event loop while another loop is running"
                     # если finally выполняется слишком близко к завершению основного asyncio.run
                     # или если dispose пытается использовать основной loop. Пробуем запустить в новом.
                     log.warning(">>> [TASK WRAPPER FINALLY] ID: %s. Got RuntimeError disposing engine, trying new event loop: %s", task_id, loop_err)
                     try:
                         # loop = asyncio.new_event_loop()
                         # loop.run_until_complete(engine.dispose())
                         # loop.close()
                         # БОЛЕЕ ПРОСТОЙ СПОСОБ запустить в новом лупе, если run упал:
                         async def _dispose_engine():
                             await engine.dispose()
                         asyncio.run(_dispose_engine())

                         log.info(">>> [TASK WRAPPER FINALLY] ID: %s. DB engine pool disposed in new loop.", task_id)
                     except Exception as dispose_final_exc:
                          log.exception(">>> [TASK WRAPPER FINALLY] ID: %s. Error disposing engine even in new loop: %s", task_id, dispose_final_exc)

                except Exception as dispose_exc:
                    log.exception(">>> [TASK WRAPPER FINALLY] ID: %s. Error disposing engine: %s", task_id, dispose_exc)
            else:
                log.warning(">>> [TASK WRAPPER FINALLY] ID: %s. Engine does not have an async dispose method.", task_id)
        else: # pragma: no cover
             log.warning(">>> [TASK WRAPPER FINALLY] ID: %s. Engine not available for disposal.", task_id)


# --- Экспорты ---
__all__ = ["celery_app", "send_due_reminders_task"]
