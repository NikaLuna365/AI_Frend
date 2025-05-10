# /app/app/core/achievements/models.py (Версия для MVP)

from __future__ import annotations
from datetime import datetime
# Используем стандартные типы Python 3.9+
from typing import List, Optional, Sequence, Union, TYPE_CHECKING

# Импорты SQLAlchemy
import sqlalchemy as sa # Для sa.true()/sa.false() если нужно
from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    Boolean,
    UniqueConstraint # Для __table_args__
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

# Импорт Base
from app.db.base import Base

# Импорт для аннотаций типов связей
if TYPE_CHECKING:
    from app.core.users.models import User


# --- Модель AchievementRule НЕ СОЗДАЕТСЯ для MVP ---
# class AchievementRule(Base):
#     __tablename__ = "achievement_rules"
#     code: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
#     title: Mapped[str] = mapped_column(String(128), nullable=False)
#     description: Mapped[Optional[str]] = mapped_column(String(256))
#     generation_context: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
#
#     achievements: Mapped[List["Achievement"]] = relationship(back_populates="rule")


# --- Модель Полученных Ачивок (Адаптирована для MVP) ---
class Achievement(Base):
    __tablename__ = "achievements"
    # Уникальный ключ на пользователя и код ачивки
    __table_args__ = (UniqueConstraint('user_id', 'code', name='uq_achievement_user_code'),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Связь с Пользователем
    user_id: Mapped[str] = mapped_column(String(64), ForeignKey('users.id', ondelete='CASCADE', name='fk_achievements_user_id'), nullable=False, index=True)
    user: Mapped["User"] = relationship(
        "app.core.users.models.User", # Полный путь к User
        back_populates="achievements"
    )

    # Код ачивки (строковый идентификатор "зашитого" правила в сервисе)
    code: Mapped[str] = mapped_column(String(64), nullable=False, index=True, comment="Identifier for the hardcoded achievement rule")

    # Поля, заполняемые после генерации
    title: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, comment="Generated title") # Может быть None до генерации
    badge_png_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True, comment="URL to the generated PNG badge in GCS")

    # --- НОВОЕ ПОЛЕ: Статус генерации ачивки ---
    # Возможные значения: "PENDING_GENERATION", "COMPLETED", "FAILED_GENERATION"
    # Используйте Enum в реальном коде
    status: Mapped[str] = mapped_column(String(32), default="PENDING_GENERATION", nullable=False, index=True)
    # ------------------------------------------

    # Временная метка получения/создания
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self) -> str: # pragma: no cover
        return f"<Achievement id={self.id} user='{self.user_id}' code='{self.code}' status='{self.status}'>"
