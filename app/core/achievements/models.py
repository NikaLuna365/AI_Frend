# /app/app/core/achievements/models.py (или аналогичный)
# ... (импорты datetime, List, Optional, SQLAlchemy типы, Base) ...
from sqlalchemy import (
    DateTime, ForeignKey, Integer, String, UniqueConstraint, Text # Добавил Text на всякий
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

# Импортируем типы из связанных модулей для аннотаций
from typing import TYPE_CHECKING, Optional, Sequence, Union # Добавил импорты
if TYPE_CHECKING:
    from app.core.users.models import User # Только для type hinting

class AchievementRule(Base):
    __tablename__ = "achievement_rules"
    code: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(256))
    # Добавим поле для хранения описания/контекста для генерации
    generation_context: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="Context/theme for LLM generation")

    # Связь один-ко-многим с полученными ачивками
    achievements: Mapped[List["Achievement"]] = relationship(back_populates="rule")

class Achievement(Base):
    __tablename__ = "achievements"
    __table_args__ = (UniqueConstraint('user_id', 'code', name='uq_achievement_user_code'),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    # --- ИСПРАВЛЕНИЕ ЗДЕСЬ: Полный путь в ForeignKey и back_populates ---
    user_id: Mapped[str] = mapped_column(String(64), ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    user: Mapped["User"] = relationship(
        "app.core.users.models.User", # <-- Полный путь
        back_populates="achievements"
    )
    # -----------------------------------------------------------------
    code: Mapped[str] = mapped_column(String(64), ForeignKey('achievement_rules.code', ondelete='CASCADE'), nullable=False, index=True)
    rule: Mapped["AchievementRule"] = relationship(back_populates="achievements") # Связь с правилом

    title: Mapped[str] = mapped_column(String(128), nullable=False, comment="Generated title")
    badge_svg_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True, comment="URL to the generated SVG badge")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
