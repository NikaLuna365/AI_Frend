# app/workers/tasks.py

from datetime import datetime, timedelta
import os

from celery import Celery

from app.config import settings
from app.core.calendar.base import get_calendar_provider
from app.core.users.service import UsersService
from app.core.users.models import User
from app.core.llm.schemas import Message

# ------------------------------------------------------------------ #
# Инициализация Celery
# ------------------------------------------------------------------ #
celery_app = Celery(
    "ai_friend",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

# В тестовом окружении – выполнять задачи синхронно
if settings.ENVIRONMENT == "test":
    celery_app.conf.update(
        task_always_eager=True,
        task_eager_propagates=True,
    )

__all__ = ["celery_app", "send_due_reminders"]

# ------------------------------------------------------------------ #
@celery_app.task(name="tasks.send_due_reminders")
def send_due_reminders():
    """
    Каждые 5 минут проверяет, есть ли у пользователей события
    на ближайший час, и отправляет им напоминания.
    """
    now = datetime.utcnow()
    upcoming = now + timedelta(hours=1)

    provider = get_calendar_provider()
    users_svc = UsersService()
    db = users_svc.db

    # Получаем всех пользователей
    user_ids = [u[0] for u in db.query(User.id).all()]
    for uid in user_ids:
        # Список событий в ближайший час
        events = provider.list_events(uid, now, upcoming)
        for ev in events:
            # Формируем текст напоминания
            text = f"Напоминание: событие '{ev.title}' начнётся в {ev.start.strftime('%Y-%m-%d %H:%M')}"
            # Сохраняем сообщение в истории чата
            users_svc.save_message(uid, Message(role="assistant", content=text))
