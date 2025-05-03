# /app/core/users/models.py (Пример для MVP)
from __future__ import annotations
from datetime import datetime
from typing import List, Optional # Добавили Optional

from sqlalchemy import (
     String, Text, DateTime, Integer, ForeignKey, UniqueConstraint, LargeBinary
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func # для server_default

from app.db.base import Base

class User(Base):
    __tablename__ = 'users'

    id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True, comment="Internal User ID")
    google_id: Mapped[Optional[str]] = mapped_column(String(255), unique=True, index=True, nullable=True, comment="Google User ID (sub)")
    email: Mapped[Optional[str]] = mapped_column(String(255), index=True, nullable=True, comment="User email (verified)")
    name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, comment="User display name")
    # timezone: Mapped[str] = mapped_column(String(64), server_default='UTC', nullable=False) # Оставим пока?
    # settings: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="User-specific settings (JSON)") # Оставим пока?
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False) # Используем timezone=True и func.now()
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Оставляем поля для токенов календаря, но они не будут использоваться в MVP
    google_calendar_access_token_encrypted: Mapped[Optional[bytes]] = mapped_column(LargeBinary, nullable=True)
    google_calendar_refresh_token_encrypted: Mapped[Optional[bytes]] = mapped_column(LargeBinary, nullable=True)
    google_calendar_token_expiry: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Связи
    messages: Mapped[List["Message"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    achievements: Mapped[List["Achievement"]] = relationship(cascade="all, delete-orphan") # Простая связь без backref в Achievement

class Message(Base):
    __tablename__ = 'messages'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[str] = mapped_column(String(64), ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(16), nullable=False) # 'user' or 'assistant'
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user: Mapped["User"] = relationship(back_populates="messages")

# --- Модели Ачивок (пример, адаптируйте под свои) ---
class AchievementRule(Base):
    __tablename__ = "achievement_rules"
    code: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(256))
    # icon_url убрали, т.к. он будет в Achievement после генерации
    # theme: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, comment="Theme hint for generation") # Добавим тему?

class Achievement(Base):
    __tablename__ = "achievements"
    __table_args__ = (UniqueConstraint('user_id', 'code', name='uq_achievement_user_code'),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[str] = mapped_column(String(64), ForeignKey('users.id', ondelete='CASCADE', name='fk_achievements_user_id'), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(64), ForeignKey('achievement_rules.code', ondelete='CASCADE', name='fk_achievements_rule_code'), nullable=False, index=True) # Используем FK к rules
    title: Mapped[str] = mapped_column(String(128), nullable=False, comment="Generated title") # Сгенерированное название
    # Используем URL для SVG бейджа
    badge_svg_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True, comment="URL to the generated SVG badge in GCS")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # rule: Mapped["AchievementRule"] = relationship() # Связь с правилом
