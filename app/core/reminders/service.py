# app/core/reminders/service.py
from __future__ import annotations

from datetime import datetime
from sqlalchemy.orm import Session

from app.db.base import Base, engine, SessionLocal
from .models import Reminder


class RemindersService:
    def __init__(self, db: Session | None = None):
        self.db = db or SessionLocal()

    # ---------------------------
    def record(self, user_id: str, text: str, fire_dt: datetime):
        self.db.add(Reminder(user_id=user_id, text=text, fire_dt=fire_dt))
        self.db.commit()

    def exists(self, user_id: str, text: str) -> bool:
        return (
            self.db.query(Reminder)
            .filter_by(user_id=user_id, text=text)
            .first()
            is not None
        )

    # only for tests
    def clear_all(self):
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
