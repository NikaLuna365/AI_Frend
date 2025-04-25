"""
ORM-модели, описывающие правила и сами достижения.

⏰  Главная правка:
    •  `code` снова является **первичным ключом** для таблицы
       `achievement_rules`. Это убирает конфликт повторного
       объявления, который ломал pytest:

       sqlalchemy.exc.ArgumentError:
         Trying to redefine primary-key column 'code' …

    •  Поле `id` нам не нужно – его убрали; если когда-нибудь
       понадобится числовой surrogate-key, миграция добавит
       его корректно через Alembic.

Всё остальное (FK из `Achievement`, каскады, repr) оставлено
как в предыдущей ревизии.
"""

from __future__ import annotations

from datetime import datetime
from typing import List

from sqlalchemy import (
    DateTime,
    ForeignKey,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from app.db.base import Base

# --------------------------------------------------------------------------- #
#                                 AchievementRule                             #
# --------------------------------------------------------------------------- #


class AchievementRule(Base):  # type: ignore[pycodestyle]
    __tablename__ = "achievement_rules"
    # если в MetaData уже есть такая таблица (из прежнего импорта в тестах) –
    # перезаписываем определение, но не пытаемся менять ее структуру
    __table_args__ = {"extend_existing": True}

    # ──────────────────────── columns ────────────────────────
    code: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
        comment="Уникальный машинный код ачивки",
        index=True,
    )
    title: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(String(256))
    icon_url: Mapped[str | None] = mapped_column(String(256))

    # ──────────────────────── relationships ────────────────────────
    achievements: Mapped[List["Achievement"]] = relationship(
        back_populates="rule",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    # -----------------------------------------------------------------------

    def __repr__(self) -> str:  # pragma: no cover
        return f"<AchievementRule {self.code!r}>"


# --------------------------------------------------------------------------- #
#                                   Achievement                              #
# --------------------------------------------------------------------------- #


class Achievement(Base):  # type: ignore[pycodestyle]
    __tablename__ = "achievements"
    __table_args__ = (
        UniqueConstraint("user_id", "code", name="uq_user_code"),
        {"extend_existing": True},
    )

    # ──────────────────────── columns ────────────────────────
    id: Mapped[int] = mapped_column(
        primary_key=True, autoincrement=True, comment="Surrogate-key"
    )
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
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

    # «денормализованные» поля, чтобы не делать join при выборке
    title: Mapped[str] = mapped_column(String(128), nullable=False)
    icon_url: Mapped[str | None] = mapped_column(String(256))

    # ──────────────────────── relationships ────────────────────────
    rule: Mapped[AchievementRule] = relationship(back_populates="achievements")

    # -----------------------------------------------------------------------

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Achievement {self.user_id}:{self.code}>"
