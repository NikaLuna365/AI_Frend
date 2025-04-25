# app/workers/tasks.py
from __future__ import annotations

from datetime import datetime, timedelta
import os

from celery import Celery

from app.config import settings
from app.core.calendar.base import get_calendar_provider
from app.core.users.service import UsersService
from app.core.users.models import User
from app.core.llm.client import Message

celery_app = Celery(
    "ai-friend",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

if settings.ENVIRONMENT == "test":
    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = True


@celery_app.task(name="tasks.send_due_reminders")
def send_due_reminders():
    now = datetime.utcnow()
    upcoming = now + timedelta(hours=1)
    provider = get_calendar_provider()
    users_svc = UsersService()
    db = users_svc.db

    uid_list = [u[0] for u in db.query(User.id).all()]
    for uid in uid_list:
        events = provider.list_events(uid, now, upcoming)
        for ev in events:
            txt = f"Напоминание: '{ev.title}' в {ev.start_dt:%Y-%m-%d %H:%M}"
            users_svc.save_message(uid, Message(role="assistant", content=txt))
    return True


__all__ = ["celery_app", "send_due_reminders"]
