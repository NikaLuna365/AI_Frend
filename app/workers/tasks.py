# app/workers/tasks.py
from __future__ import annotations

from celery import Celery

from app.config import settings
from app.core.reminders.service import RemindersService

celery_app = Celery(
    "ai-friend",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

# ─────────────────────────────  tasks  ────────────────────────────────────
@celery_app.task(name="send_due_reminders")
def send_due_reminders() -> None:
    """Отправить напоминания, срок которых наступил."""
    svc = RemindersService()
    due = svc.list_due()
    for r in due:
        # … уведомление по-email / push …
        svc.mark_sent(r.id)
