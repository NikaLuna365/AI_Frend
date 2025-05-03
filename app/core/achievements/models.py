# /app/app/core/achievements/models.py (Исправленная версия с импортами)

from __future__ import annotations
from datetime import datetime
# Используем стандартные типы Python 3.9+
from typing import List, Optional, Sequence, Union, TYPE_CHECKING

# --- ВАЖНО: Импортируем sqlalchemy как sa и нужные типы ---
import sqlalchemy as sa
from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,  # Добавил Text для description/generation_context
    Boolean, # Если будет использоваться
    UniqueConstraint # Для __table_args__
)
# -------------------------------------------------------
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

# --- Импорт Base ---
from app.db.base import Base # Убедитесь, что путь app.db.base верный
# --------------------

# Импорт для аннотаций типов связей
if TYPE_CHECKING:
    from app.core.users.models import User


# --- Модель Правил Ачивок ---
class AchievementRule(Base):
    __tablename__ = "achievement_rules"
    # __table_args__ = {"extend_existing": True} # Убрано, т.к. начинаем с чистой БД

    code: Mapped[str] = mapped_column(String(64), primary_key=True, index=True) # OK
    title: Mapped[str] = mapped_column(String(128), nullable=False) # OK
    description: Mapped[Optional[str]] = mapped_column(String(256), nullable=True) # OK
    generation_context: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="Context/theme for LLM generation") # OK (Text импортирован)

    # Связь один-ко-многим с полученными ачивками
    achievements: Mapped[List["Achievement"]] = relationship(
        "Achievement", # Если Achievement в этом же файле
        back_populates="rule",
        cascade="all, delete-orphan" # Удаляем ачивки при удалении правила
    )

    def __repr__(self) -> str: # pragma: no cover
        return f"<AchievementRule code={self.code!r}>"


# --- Модель Полученных Ачивок ---
class Achievement(Base):
    __tablename__ = "achievements"
    # Уникальный ключ на пользователя и код ачивки
    __table_args__ = (UniqueConstraint('user_id', 'code', name='uq_achievement_user_code'),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True) # OK (Integer импортирован)

    # Связь с Пользователем
    user_id: Mapped[str] = mapped_column(String(64), ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True) # OK (String, ForeignKey импортированы)
    user: Mapped["User"] = relationship(
        "app.core.users.models.User", # Полный путь к User
        back_populates="achievements"
    )

    # Связь с Правилом Ачивки
    code: Mapped[str] = mapped_column(String(64), ForeignKey('achievement_rules.code', ondelete='CASCADE'), nullable=False, index=True) # OK
    rule: Mapped["AchievementRule"] = relationship(
        "AchievementRule", # Если AchievementRule в этом же файле
        back_populates="achievements"
        # lazy="joined" # Можно выбрать стратегию загрузки правила
    )

    # Денормализованные/Сгенерированные поля
    title: Mapped[str] = mapped_column(String(128), nullable=False, comment="Generated title") # OK
    badge_svg_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True, comment="URL to the generated SVG badge") # OK

    # Временная метка получения
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False) # OK (DateTime импортирован)

    def __repr__(self) -> str: # pragma: no cover
        return f"<Achievement id={self.id} user_id={self.user_id!r} code={self.code!r}>"
