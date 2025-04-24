# app/core/achievements/models.py
"""
SQLAlchemy-модели для подсистемы «Achievements».

Содержит две таблицы:

    1. AchievementRule  ― справочник правил (код, заголовок, иконка, описание),
                          по сути «каталог достижений».
    2. Achievement      ― конкретная медаль, которую получил пользователь
                          (user_id + code правила).

Эти модели используются сервисом AchievementsService, API-эндпоинтом /v1/achievements
и Alembic-миграциями.
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
from sqlalchemy.orm import (
    DeclarativeMeta,
    relationship,
)

from app.db.base import Base  # DeclarativeBase из единой точки


class AchievementRule(Base):  # type: ignore[misc]  # mypy из-за DeclarativeMeta
    """
    Каталог правил достижений (одна запись = один возможный бейдж).
    """

    __tablename__: str = "achievement_rules"

    # --- колонки -------------------------------------------------------------

    code: str = Column(String, primary_key=True, doc="Уникальный код достижения")
    title: str = Column(String, nullable=False, doc="Человекочитаемый заголовок")
    icon_url: str = Column(String, nullable=False, doc="URL SVG/PNG иконки")
    description: str | None = Column(
        Text, nullable=True, doc="Описание правила (не обязательно)"
    )

    # --- repr / str ----------------------------------------------------------

    def __repr__(self) -> str:  # pragma: no cover
        return f"<AchievementRule code={self.code!r} title={self.title!r}>"


class Achievement(Base):  # type: ignore[misc]
    """
    Конкретная медаль, присуждённая пользователю.
    """

    __tablename__: str = "achievements"

    # --- колонки -------------------------------------------------------------

    id: int = Column(Integer, primary_key=True, autoincrement=True, index=True)
    user_id: int = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="FK на users.id",
    )
    code: str = Column(
        String,
        ForeignKey("achievement_rules.code", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="FK на achievement_rules.code",
    )
    title: str = Column(String, nullable=False, doc="Копия заголовка на момент выдачи")
    icon_url: str = Column(String, nullable=False, doc="Копия URL иконки на момент выдачи")
    created_at: datetime = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        doc="Когда медаль была выдана",
    )

    # --- связи ---------------------------------------------------------------

    rule: "AchievementRule" = relationship("AchievementRule", lazy="joined")

    # --- repr / str ----------------------------------------------------------

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<Achievement id={self.id} user_id={self.user_id} "
            f"code={self.code!r} created_at={self.created_at}>"
        )
