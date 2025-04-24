import logging
from celery import Celery
from datetime import datetime, timedelta

from app.config import settings
from app.core.calendar.base import get_calendar_provider
from app.core.users.service import UsersService
from app.core.reminders.service import RemindersService
from app.core.llm.client import Message

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

# Инициализация Celery
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
    logger.info(f"send_due_reminders started: checking events from {now} to {upcoming}")

    provider = get_calendar_provider()
    users_svc = UsersService()
    reminders_svc = RemindersService()

    # Получаем всех пользователей
    try:
        user_ids = [u.id for u in users_svc.db.query(UsersService.model).all()]
    except Exception as err:
        logger.error(f"Error fetching users: {err}")
        return False

    for uid in user_ids:
        try:
            events = provider.list_events(uid, now, upcoming)
            for ev in events:
                # ev должен содержать атрибут id
                ev_id = getattr(ev, 'id', None) or f"{ev.title}-{ev.start.isoformat()}"
                if reminders_svc.exists(uid, ev_id):
                    continue
                text = f"Напоминание: событие '{ev.title}' начнётся в {ev.start.strftime('%Y-%m-%d %H:%M')}"
                users_svc.save_message(uid, Message(role='assistant', content=text))
                reminders_svc.record(uid, ev_id)
                logger.info(f"Sent reminder to user {uid} for event {ev_id}")
        except Exception as e:
            logger.error(f"Error sending reminders for user {uid}: {e}")
    logger.info("send_due_reminders completed")
    return True
