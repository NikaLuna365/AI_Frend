# /app/app/core/users/models.py (ФИНАЛЬНАЯ ИСПРАВЛЕННАЯ ВЕРСИЯ v3)

from __future__ import annotations
from datetime import datetime
from typing import List, Optional, TYPE_CHECKING

# --- ВАЖНО: Импортируем sqlalchemy как sa ---
import sqlalchemy as sa # <--- ДОБАВЛЕН ИМПОРТ sqlalchemy as sa
# ------------------------------------------

# --- Импорты типов SQLAlchemy ---
from sqlalchemy import (
    String,
    DateTime,
    ForeignKey,
    Integer,
    Text,
    Boolean,
    LargeBinary,
    UniqueConstraint # Добавил UniqueConstraint для использования в __table_args__
)
# -------------------------------------
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

# --- Импорт Base ---
from app.db.base import Base # Убедитесь, что путь app.db.base верный
# --------------------

# Импорты для аннотаций типов связей
if TYPE_CHECKING:
    from app.core.achievements.models import Achievement


# --- Модель Пользователя ---
class User(Base):
    __tablename__ = 'users'
    # Опционально: Явно укажем schema, если она используется в Postgres
    # __table_args__ = {'schema': 'public'} # Или ваша схема

    id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    google_id: Mapped[Optional[str]] = mapped_column(String(255), unique=True, index=True, nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), index=True, nullable=True, unique=True) # Email тоже должен быть уникальным, если используется для поиска
    name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    # Используем sa.true() для server_default
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, server_default=sa.true()) # Теперь 'sa' определен
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Поля для токенов календаря
    google_calendar_access_token_encrypted: Mapped[Optional[bytes]] = mapped_column(LargeBinary, nullable=True)
    google_calendar_refresh_token_encrypted: Mapped[Optional[bytes]] = mapped_column(LargeBinary, nullable=True)
    google_calendar_token_expiry: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # --- Связи ---
    messages: Mapped[List["Message"]] = relationship(
        "Message",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    achievements: Mapped[List["Achievement"]] = relationship(
        "app.core.achievements.models.Achievement",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin"
    )

    def __repr__(self) -> str: # pragma: no cover
        return f"<User id={self.id!r} name={self.name!r}>"


# --- Модель Сообщения ---
class Message(Base):
    __tablename__ = 'messages'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[str] = mapped_column(String(64), ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="messages")

    def __repr__(self) -> str: # pragma: no cover
        return f"<Message id={self.id} user_id={self.user_id!r} role={self.role!r}>"
