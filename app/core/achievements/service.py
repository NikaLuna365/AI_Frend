# app/core/achievements/service.py

"""
Сервис, отвечающий за выдачу и хранение достижений (медалей).
"""

from __future__ import annotations

from datetime import datetime
from typing import Iterable

from app.db.base import SessionLocal
from app.core.achievements.models import Achievement
from app.core.achievements.schemas import AchievementOut


class AchievementsService:
    """Бизнес-логика работы с медалями."""

    def __init__(self, db_session: SessionLocal | None = None) -> None:
        self.db = db_session or SessionLocal()

    # ----------------- публичные методы -----------------

    def get_user_achievements(self, user_id: int) -> list[AchievementOut]:
        """Вернуть все достижения пользователя."""
        achievements: Iterable[Achievement] = (
            self.db.query(Achievement).filter(Achievement.user_id == user_id).all()
        )
        return [AchievementOut.model_validate(a) for a in achievements]

    def grant_achievement(
        self,
        user_id: int,
        code: str,
        title: str,
        icon_url: str | None = None,
    ) -> AchievementOut:
        """Создать (или вернуть существующее) достижение для пользователя."""
        achievement: Achievement | None = (
            self.db.query(Achievement)
            .filter(
                Achievement.user_id == user_id,
                Achievement.code == code,
            )
            .one_or_none()
        )

        if achievement is None:
            achievement = Achievement(
                user_id=user_id,
                code=code,
                title=title,
                icon_url=icon_url,
                created_at=datetime.utcnow(),
            )
            self.db.add(achievement)
            self.db.commit()
            self.db.refresh(achievement)

        return AchievementOut.model_validate(achievement)
