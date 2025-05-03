# /app/app/core/users/models.py (ФИНАЛЬНАЯ ИСПРАВЛЕННАЯ ВЕРСИЯ v2)

from __future__ import annotations
from datetime import datetime
from typing import List, Optional, TYPE_CHECKING # Добавляем TYPE_CHECKING

# --- ВАЖНО: ИМПОРТ ТИПОВ SQLAlchemy ---
from sqlalchemy import (
    String,
    DateTime,
    ForeignKey,
    Integer,
    Text,
    Boolean,        # Добавляем Boolean для is_active
    LargeBinary     # Добавляем LargeBinary для шифрованных токенов
)
# -------------------------------------
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

# --- Импорт Base (уже должен быть) ---
from app.db.base import Base
# -----------------------------------

# Импорты для аннотаций типов связей
if TYPE_CHECKING:
    from app.core.achievements.models import Achievement


# --- Модель Пользователя ---
class User(Base):
    __tablename__ = 'users'

    id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True) # OK
    google_id: Mapped[Optional[str]] = mapped_column(String(255), unique=True, index=True, nullable=True) # OK
    email: Mapped[Optional[str]] = mapped_column(String(255), index=True, nullable=True) # OK
    name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True) # OK
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, server_default=sa.true()) # OK (Boolean импортирован)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False) # OK (DateTime импортирован)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False) # OK

    # Поля для токенов календаря
    google_calendar_access_token_encrypted: Mapped[Optional[bytes]] = mapped_column(LargeBinary, nullable=True) # OK (LargeBinary импортирован)
    google_calendar_refresh_token_encrypted: Mapped[Optional[bytes]] = mapped_column(LargeBinary, nullable=True) # OK
    google_calendar_token_expiry: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True) # OK

    # --- Связи ---
    messages: Mapped[List["Message"]] = relationship(
        "Message",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    achievements: Mapped[List["Achievement"]] = relationship(
        "app.core.achievements.models.Achievement", # Полный путь
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin"
    )

    def __repr__(self) -> str: # pragma: no cover
        return f"<User id={self.id!r} name={self.name!r}>"


# --- Модель Сообщения ---
class Message(Base):
    __tablename__ = 'messages'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True) # OK (Integer импортирован)
    user_id: Mapped[str] = mapped_column(String(64), ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True) # OK (String, ForeignKey импортированы)
    role: Mapped[str] = mapped_column(String(16), nullable=False) # OK
    content: Mapped[str] = mapped_column(Text, nullable=False) # OK (Text импортирован)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False) # OK

    # Связь с User
    user: Mapped["User"] = relationship("User", back_populates="messages")

    def __repr__(self) -> str: # pragma: no cover
        return f"<Message id={self.id} user_id={self.user_id!r} role={self.role!r}>"
