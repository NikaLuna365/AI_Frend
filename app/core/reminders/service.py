from sqlalchemy.orm import Session
from app.db.base import SessionLocal
from .models import Reminder

class RemindersService:
    def __init__(self):
        self.db: Session = SessionLocal()

    def exists(self, user_id: str, event_id: str) -> bool:
        return self.db.query(Reminder).filter_by(user_id=user_id, event_id=event_id).first() is not None

    def record(self, user_id: str, event_id: str):
        reminder = Reminder(user_id=user_id, event_id=event_id)
        self.db.add(reminder)
        self.db.commit()
