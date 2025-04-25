# app/workers/tasks.py
from celery import Celery
from datetime import datetime, timedelta

from app.config import settings
from app.core.calendar.base import get_calendar_provider
from app.core.users.service import UsersService
from app.db.base import SessionLocal  # если нужно напрямую
from app.core.users.models import User
from app.core.llm.client import Message

# Инициализация Celery в атрибуте `app`
app = Celery(
    "worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

@app.task(name="tasks.send_due_reminders")
def send_due_reminders():
    """
    Каждые 5 минут проверяет события у всех пользователей
    на ближайший час и отправляет напоминание в чат.
    """
    now = datetime.utcnow()
    upcoming = now + timedelta(hours=1)
    provider = get_calendar_provider()
    users_svc = UsersService()
    db = users_svc.db

    user_ids = [u[0] for u in db.query(User.id).all()]
    for uid in user_ids:
        events = provider.list_events(uid, now, upcoming)
        for ev in events:
            text = f"Напоминание: событие '{ev.title}' начнётся в {ev.start_dt.strftime('%Y-%m-%d %H:%M')}"
            users_svc.save_message(uid, Message(role="assistant", content=text))
    return True
