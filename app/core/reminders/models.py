# app/core/reminders/models.py

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,  # Import Column for compatibility if needed, though Mapped is preferred
    DateTime,
    ForeignKey,
    Integer,
    String,
    Index,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Reminder(Base):
    """
    ORM модель для Напоминаний.

    Содержит информацию о том, кому, когда и о чем напомнить,
    а также статус отправки.
    """
    __tablename__ = 'reminders'

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True
    )
    user_id: Mapped[str] = mapped_column(
        String, ForeignKey('users.id', ondelete='CASCADE'), index=True, nullable=False
    )
    # Содержимое напоминания
    title: Mapped[str] = mapped_column(String, nullable=False)
    # Время, когда напоминание должно быть отправлено (UTC)
    due_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    # Флаг, указывающий, было ли напоминание отправлено
    sent: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, index=True
    )
    # Время создания записи (UTC)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    # Опциональная ссылка на событие календаря, из которого могло
    # быть создано напоминание (если применимо).
    # Формат может быть `provider_name:event_provider_id`.
    source_event_id: Mapped[str | None] = mapped_column(String, nullable=True)

    # Опционально: Связь с пользователем, если нужна (может быть полезна)
    # user: Mapped["User"] = relationship(back_populates="reminders") # Если в User добавить backref

    # Добавляем индексы для часто используемых полей в запросах
    __table_args__ = (
        Index('ix_reminders_due_at_sent', 'due_at', 'sent'),
        {"extend_existing": True}, # Для тестов, если модель переопределяется
    )

    def __repr__(self) -> str: # pragma: no cover
        """
        Возвращает строковое представление объекта Reminder.

        Returns:
            str: Строка вида "<Reminder id=1 user_id='u1' due='2024-07-15T10:00:00' sent=False>".
        """
        due_str = self.due_at.strftime('%Y-%m-%dT%H:%M:%S')
        return f"<Reminder id={self.id} user_id={self.user_id!r} due='{due_str}' sent={self.sent}>"
