# /app/app/core/users/models.py (Финальная Исправленная Версия)

from __future__ import annotations
from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
     String, Text, DateTime, Integer, ForeignKey, UniqueConstraint, LargeBinary, Boolean
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

# --- ВАЖНО: ИСПРАВЛЕН ИМПОРТ Base ---
# Импортируем Base из файла, где он определен (обычно app/db/base.py)
from app.db.base import Base # <--- УБЕДИТЕСЬ, ЧТО ПУТЬ ВЕРНЫЙ
# ---------------------------------

# Импортируем типы из связанных модулей для аннотаций
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    # Путь к модели Achievement должен быть правильным
    from app.core.achievements.models import Achievement


class User(Base): # Теперь 'Base' определена
    __tablename__ = 'users'

    # Внутренний ID пользователя
    id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)

    # Поля, связанные с Google Auth (оставляем для будущего, но nullable=True)
    google_id: Mapped[Optional[str]] = mapped_column(String(255), unique=True, index=True, nullable=True, comment="Google User ID (sub)")
    email: Mapped[Optional[str]] = mapped_column(String(255), index=True, nullable=True, comment="User email (verified from Google)")

    name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, comment="User display name")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Поля для временных меток
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Поля для токенов календаря (оставляем для будущего, nullable=True)
    google_calendar_access_token_encrypted: Mapped[Optional[bytes]] = mapped_column(LargeBinary, nullable=True)
    google_calendar_refresh_token_encrypted: Mapped[Optional[bytes]] = mapped_column(LargeBinary, nullable=True)
    google_calendar_token_expiry: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # --- Связи ---
    messages: Mapped[List["Message"]] = relationship(
        "Message",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    achievements: Mapped[List["Achievement"]] = relationship(
        "app.core.achievements.models.Achievement", # Полный путь
        back_populates="user",
        cascade="all, delete-orphan"
    )


class Message(Base): # 'Base' здесь тоже должна быть видна
    __tablename__ = 'messages'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[str] = mapped_column(String(64), ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(16), nullable=False) # 'user' or 'assistant'
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Связь с User
    user: Mapped["User"] = relationship("User", back_populates="messages")
