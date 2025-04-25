# app/core/achievements/models.py

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

"""
ORM-модели ачивок.

Важно: импортируем общий Base из app.db.base — это убирает ошибку
«Table 'achievement_rules' is already defined …».
"""

# --------------------------------------------------------------------------- #
#                               AchievementRule                               #
# --------------------------------------------------------------------------- #

class AchievementRule(Base):  # type: ignore[pycodestyle]
    __tablename__ = "achievement_rules"
    __table_args__ = {
        # При повторном импорте модели позволяет переопределять таблицу
        "extend_existing": True,
    }

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    code: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(
        String(128), nullable=False
    )
    description: Mapped[str | None] = mapped_column(
        String(256), nullable=True
    )
    icon_url: Mapped[str | None] = mapped_column(
        String(256), nullable=True
    )

    achievements: Mapped[list[Achievement]] = relationship(
        "Achievement",
        back_populates="rule",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<AchievementRule code={self.code!r} title={self.title!r}>"


# --------------------------------------------------------------------------- #
#                                Achievement                                  #
# --------------------------------------------------------------------------- #

class Achievement(Base):  # type: ignore[pycodestyle]
    __tablename__ = "achievements"
    __table_args__ = (
        UniqueConstraint("user_id", "code", name="uq_user_code"),
        {"extend_existing": True},
    )

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    user_id: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True
    )
    code: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("achievement_rules.code", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )

    # Снапшот полей правила на момент получения
    title: Mapped[str] = mapped_column(
        String(128), nullable=False
    )
    icon_url: Mapped[str | None] = mapped_column(
        String(256), nullable=True
    )

    rule: Mapped[AchievementRule] = relationship(
        "AchievementRule",
        back_populates="achievements",
        lazy="joined",
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Achievement user={self.user_id!r} code={self.code!r}>"
