# /app/app/core/users/models.py (ФИНАЛЬНАЯ ИСПРАВЛЕННАЯ ВЕРСИЯ)

from __future__ import annotations
from datetime import datetime
# Используем стандартные типы Python 3.9+ для аннотаций
from typing import List, Optional

# Импорты SQLAlchemy для типов данных и ORM
from sqlalchemy import (
     String, Text, DateTime, Integer, ForeignKey, UniqueConstraint, LargeBinary, Boolean
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func # Для server_default=func.now()

# --- ГАРАНТИРОВАННЫЙ ИМПОРТ Base ---
# Базовый декларативный класс импортируется из app.db.base, где он определен.
# Если у вас Base определен в другом месте (например, app.db.base_class),
# ИЗМЕНИТЕ ПУТЬ ИМПОРТА здесь соответственно.
from app.db.base import Base
# -----------------------------------

# Импорты для аннотаций типов связей (избегаем циклических импортов)
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    # Убедитесь, что этот путь корректен для вашей структуры
    from app.core.achievements.models import Achievement


# --- Модель Пользователя ---
class User(Base): # Теперь Base ОПРЕДЕЛЕНА перед использованием
    __tablename__ = 'users'

    # Внутренний ID пользователя (генерируется сервисом)
    id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)

    # Поля для Google Sign-In (nullable=True, т.к. не используются в MVP логине)
    google_id: Mapped[Optional[str]] = mapped_column(String(255), unique=True, index=True, nullable=True, comment="Google User ID (sub)")
    email: Mapped[Optional[str]] = mapped_column(String(255), index=True, nullable=True, comment="User email")

    # Основные поля профиля
    name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, comment="User display name")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, server_default=sa.true()) # Добавил server_default

    # Временные метки
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Поля для токенов календаря (оставляем для будущего)
    google_calendar_access_token_encrypted: Mapped[Optional[bytes]] = mapped_column(LargeBinary, nullable=True)
    google_calendar_refresh_token_encrypted: Mapped[Optional[bytes]] = mapped_column(LargeBinary, nullable=True)
    google_calendar_token_expiry: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # --- Связи ---
    messages: Mapped[List["Message"]] = relationship(
        "Message", # Имя класса как строка
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin" # Пример стратегии загрузки (опционально)
    )
    achievements: Mapped[List["Achievement"]] = relationship(
        "app.core.achievements.models.Achievement", # Полный путь
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin" # Пример стратегии загрузки
    )

    def __repr__(self) -> str: # pragma: no cover
        return f"<User id={self.id!r} name={self.name!r}>"


# --- Модель Сообщения ---
class Message(Base): # Base здесь тоже видна
    __tablename__ = 'messages'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[str] = mapped_column(String(64), ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(16), nullable=False) # 'user' or 'assistant'
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Связь с User
    user: Mapped["User"] = relationship("User", back_populates="messages")

    def __repr__(self) -> str: # pragma: no cover
        return f"<Message id={self.id} user_id={self.user_id!r} role={self.role!r}>"
