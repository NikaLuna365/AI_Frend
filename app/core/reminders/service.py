from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import select, delete
from sqlalchemy.orm import Session

from app.db.base import get_db_session, Base
from app.config import settings

# ---- simple table ---------------------------------------------------
from sqlalchemy import Column, Integer, String, DateTime  # noqa: E402

class Reminder(Base):  # type: ignore[misc]
    __tablename__ = "reminders"

    id = Column(Integer, primary_key=True)
    user_id = Column(String, nullable=False)
    text = Column(String, nullable=False)
    due_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


# ---- service --------------------------------------------------------
class RemindersService:
    def __init__(self, db: Session | None = None) -> None:
        self.db = db or next(get_db_session())  # for CLI / Celery

    # used only in tests
    def clear_all(self) -> None:
        self.db.execute(delete(Reminder))
        self.db.commit()

    def record(self, user_id: str, text: str, due: datetime) -> None:
        self.db.add(Reminder(user_id=user_id, text=text, due_at=due))

    def exists(self, user_id: str, text: str) -> bool:
        stmt = select(Reminder).where(Reminder.user_id == user_id, Reminder.text == text)
        return self.db.scalar(stmt) is not None

    def process_due(self) -> int:
        now = datetime.utcnow()
        stmt = select(Reminder).where(Reminder.due_at <= now)
        due_list = self.db.scalars(stmt).all()

        # here you would send messages; we just delete
        if due_list:
            self.db.execute(
                delete(Reminder).where(Reminder.id.in_(r.id for r in due_list))
            )
        self.db.commit()
        return len(due_list)
