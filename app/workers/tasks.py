from __future__ import annotations

import logging
import os

from celery import Celery

from app.config import settings
from app.core.reminders.service import RemindersService

log = logging.getLogger(__name__)

celery_app = Celery(
    "ai-friend",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)
celery_app.conf.update(task_track_started=True, timezone="UTC")

__all__ = ["celery_app"]  # для -A app.workers.tasks:celery_app


@celery_app.task(name="reminders.send_due")
def send_due_reminders() -> None:  # noqa: D401
    svc = RemindersService()
    sent = svc.process_due()
    log.info("[Celery] send_due_reminders processed=%d pid=%s", sent, os.getpid())
