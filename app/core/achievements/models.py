# app/core/achievements/models.py
"""
SQLAlchemy-модели для подсистемы «Achievements».

Таблицы:
    achievement_rules  – справочник возможных достижений;
    achievements       – конкретные медали пользователей.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeMeta, relationship

from app.db.base import Base


class AchievementRule(Base):  # type: ignore[misc]
    """Каталог правил достижений."""

    __tablename__ = "achievement_rules"

    code = Column(String, primary_key=True, doc="Уникальный код бейджа")
    title = Column(String, nullable=False, doc="Заголовок бейджа")
    icon_url = Column(String, nullable=False, doc="URL иконки (PNG/SVG)")
    description = Column(Text, nullable=True, doc="Описание условия получения")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<AchievementRule code={self.code!r} title={self.title!r}>"


class Achievement(Base):  # type: ignore[misc]
    """Конкретная медаль, присуждённая пользователю."""

    __tablename__ = "achievements"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="FK → users.id",
    )
    code = Column(
        String,
        ForeignKey("achievement_rules.code", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="FK → achievement_rules.code",
    )
    title = Column(String, nullable=False, doc="Копия title на момент выдачи")
    icon_url = Column(String, nullable=False, doc="Копия icon_url на момент выдачи")
    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        doc="Время выдачи",
    )

    # связь с правилом (без статической аннотации во избежание MappedAnnotationError)
    rule = relationship("AchievementRule", lazy="joined")

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<Achievement id={self.id} user_id={self.user_id} "
            f"code={self.code!r} created_at={self.created_at}>"
        )
