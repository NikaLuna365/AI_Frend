# /app/app/core/achievements/models.py (Версия для MVP без AchievementRule - ПОДТВЕРЖДАЕМ)

from __future__ import annotations
from datetime import datetime
from typing import List, Optional, Sequence, Union, TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy import (
    DateTime, ForeignKey, Integer, String, Text, Boolean, UniqueConstraint
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base import Base

if TYPE_CHECKING:
    from app.core.users.models import User

# --- Модель AchievementRule НЕ ИСПОЛЬЗУЕТСЯ и УДАЛЕНА/ЗАКОММЕНТИРОВАНА ---

class Achievement(Base):
    __tablename__ = "achievements"
    __table_args__ = (UniqueConstraint('user_id', 'code', name='uq_achievement_user_code'),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[str] = mapped_column(String(64), ForeignKey('users.id', ondelete='CASCADE', name='fk_achievements_user_id'), nullable=False, index=True)
    user: Mapped["User"] = relationship("app.core.users.models.User", back_populates="achievements")
    code: Mapped[str] = mapped_column(String(64), nullable=False, index=True, comment="Identifier for the hardcoded achievement trigger")
    title: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, comment="Generated title")
    badge_png_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True, comment="URL to the generated PNG badge in GCS")
    status: Mapped[str] = mapped_column(String(32), default="PENDING_GENERATION", nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self) -> str: # pragma: no cover
        return f"<Achievement id={self.id} user='{self.user_id}' code='{self.code}' status='{self.status}'>"
