"""
ORM-модели ачивок.

Важно: импортируем общий Base из app.db.base -- это убирает ошибку
«Table 'achievement_rules' is already defined …».
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

# --------------------------------------------------------------------------- #
#                               AchievementRule                               #
# --------------------------------------------------------------------------- #


class AchievementRule(Base):  # type: ignore[pycodestyle]
    __tablename__ = "achievement_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str] = mapped_column(String(256), nullable=True)
    icon_url: Mapped[str | None] = mapped_column(String(256))

    achievements: Mapped[list["Achievement"]] = relationship(
        back_populates="rule", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<AchievementRule {self.code!r}>"


# --------------------------------------------------------------------------- #
#                                Achievement                                  #
# --------------------------------------------------------------------------- #


class Achievement(Base):  # type: ignore[pycodestyle]
    __tablename__ = "achievements"
    __table_args__ = (
        UniqueConstraint("user_id", "code", name="uq_user_code"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    code: Mapped[str] = mapped_column(
        String(64), ForeignKey("achievement_rules.code"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    rule: Mapped[AchievementRule] = relationship(back_populates="achievements")

    # краткие алиасы – чтобы удобнее в сервисах
    title: Mapped[str] = mapped_column(String(128), nullable=False)
    icon_url: Mapped[str | None] = mapped_column(String(256))

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Achievement {self.user_id}:{self.code}>"
