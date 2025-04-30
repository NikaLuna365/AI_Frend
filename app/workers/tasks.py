# app/workers/tasks.py (Упрощенная версия для диагностики)
# ... (импорты, настройка Celery, расписание - ОСТАВЛЯЕМ КАК БЫЛО) ...

@celery_app.task(name="app.workers.tasks.send_due_reminders_task", bind=True)
async def send_due_reminders_task(self) -> str:
    log.info("Starting DIAGNOSTIC send_due_reminders_task (Task ID: %s)...", self.request.id)
    result_message = "Task started (diagnostic)."
    try:
        async with async_session_context() as session: # <- Проверяем контекст
            log.info("Session opened successfully.")
            svc = RemindersService(session) # <- Проверяем создание сервиса

            # --- Вызов 1: list_due_and_unsent ---
            log.info("Calling list_due_and_unsent...")
            due_reminders = await svc.list_due_and_unsent() # <- Проверяем первый await
            log.info("list_due_and_unsent returned %d reminders.", len(due_reminders))

            # --- ВРЕМЕННО УБИРАЕМ ЦИКЛ И MARK_SENT ---
            # if due_reminders:
            #     first_reminder_id = due_reminders[0].id
            #     log.info("Calling mark_sent for reminder id=%d...", first_reminder_id)
            #     await svc.mark_sent(first_reminder_id) # <- Проверяем второй await
            #     log.info("mark_sent completed.")
            #     result_message = f"Task completed, processed first reminder {first_reminder_id}."
            # else:
            #     result_message = "Task completed, no reminders found."
            result_message = f"Task completed after list_due_and_unsent. Found {len(due_reminders)} reminders."


        log.info(result_message)
        return result_message # Возвращаем простую строку

    except Exception as e:
        log.exception(
            "CRITICAL error in DIAGNOSTIC send_due_reminders_task (Task ID: %s): %s",
            self.request.id, e
        )
        # Перебрасываем для регистрации ошибки в Celery
        raise e
