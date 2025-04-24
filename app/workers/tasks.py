from celery import Celery
from app.config import settings
from app.core.calendar.base import get_calendar_provider
from app.core.users.service import UsersService
from app.core.reminders.service import RemindersService
from app.core.llm.client import Message
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)
celery_app = Celery(
    'worker',
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND
)

@celery_app.task(name='tasks.send_due_reminders')
def send_due_reminders():
    """
    Каждые 5 минут проверяет события у всех пользователей
    на ближайший час и отправляет единичное напоминание.
    """
    now = datetime.utcnow()
    upcoming = now + timedelta(hours=1)
    provider = get_calendar_provider()
    users_svc = UsersService()
    reminders_svc = RemindersService()

    logger.info(f"Running send_due_reminders at {now.isoformat()}")
    # получить всех пользователей
    user_ids = [uid for uid, in users_svc.db.query(users_svc.db.query(UsersService.model).with_entities(UsersService.model.id))]
    for uid in user_ids:
        try:
            events = provider.list_events(uid, now, upcoming)
            for ev in events:
                # проверка, был ли уже отправлен reminder для этой event_id
                if reminders_svc.exists(uid, ev.id):
                    continue
                text = f"Напоминание: событие '{ev.title}' начнётся в {ev.start.strftime('%Y-%m-%d %H:%M')}"
                users_svc.save_message(uid, Message(role='assistant', content=text))
                reminders_svc.record(uid, ev.id)
                logger.info(f"Sent reminder to {uid} for event {ev.id}")
        except Exception as e:
            logger.error(f"Error sending reminders for user {uid}: {e}")
    return True
