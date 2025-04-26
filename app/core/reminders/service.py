"""Service-layer for Reminders."""

from __future__ import annotations

from datetime import datetime
from typing import List

from app.db.base import get_db_session, Session
from .models import Reminder  # ваша ORM-модель

class RemindersService:
    """Business-logic around reminders."""

    def __init__(self, db: Session | None = None) -> None:
        # В Celery-тасках нет FastAPI-DI, берём ручками
        self.db = db or next(get_db_session())

    # ------------------------------------------------------------------ #
    #                       public business-methods                       #
    # ------------------------------------------------------------------ #
    def list_due(self) -> List[Reminder]:
        """Все напоминания, время которых <= UTC now."""
        return (
            self.db.query(Reminder)
            .filter(Reminder.due <= datetime.utcnow())
            .all()
        )

    # … остальные методы (create, delete, …) …
