# app/core/achievements/service.py
from __future__ import annotations

from datetime import datetime
from typing import List

from sqlalchemy.orm import Session

from app.db.base import SessionLocal, Base, engine
from .models import Achievement
from .schemas import AchievementOut, Event


class AchievementsService:
    def __init__(self, db: Session | None = None) -> None:
        self.db = db or SessionLocal()

    # ------------------------------------------------------------------ #
    def list_user_achievements(self, user_id: str) -> List[AchievementOut]:
        rows = (
            self.db.query(Achievement)
            .filter(Achievement.user_id == user_id)
            .order_by(Achievement.created_at)
            .all()
        )
        return [AchievementOut.model_validate(r.__dict__) for r in rows]

    get_user_achievements = list_user_achievements  # b/c

    # ------------------------------------------------------------------ #
    def check_and_award(
        self,
        user_id: str,
        events: List[Event],
        reply_text: str,
    ) -> List[AchievementOut]:
        """Заглушка: в MVP просто ничего не выдаём."""
        return []
