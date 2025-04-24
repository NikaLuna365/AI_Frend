from sqlalchemy import Column, String, DateTime, Integer, ForeignKey
from app.db.base import Base
from datetime import datetime

class Reminder(Base):
    __tablename__ = 'reminders'
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, ForeignKey('users.id', ondelete='CASCADE'), index=True)
    event_id = Column(String, nullable=False)
    sent_at = Column(DateTime, default=datetime.utcnow)
