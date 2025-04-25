from __future__ import annotations

import logging
from datetime import datetime
from typing import Iterable, List

from sqlalchemy import select, delete
from sqlalchemy.orm import Session

from app.db.base import Base, get_db_session
from sqlalchemy import Column, Integer, String, DateTime  # noqa: E402

log = logging.getLogger(__name__)


class AchievementRule(Base):  # type: ignore[misc]
    __tablename__ = "achievement_rules"
    code = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    description = Column(String, nullable=False)
    icon_url = Column(String, nullable=True)


class Achievement(Base):  # type: ignore[misc]
    __tablename__ = "achievements"
    id = Column(Integer, primary_key=True)
    user_id = Column(String, nullable=False)
    code = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class AchievementOut(dict):  # simple serialisable
    pass


class AchievementsService:
    def __init__(self, db: Session | None = None) -> None:
        self.db = db or next(get_db_session())

    # --------------------------------------------------------------
    def list_user_achievements(self, user_id: str) -> List[AchievementOut]:
        rows = (
            self.db.query(Achievement, AchievementRule)
            .join(AchievementRule, Achievement.code == AchievementRule.code)
            .filter(Achievement.user_id == user_id)
            .order_by(Achievement.created_at)
            .all()
        )
        return [
            AchievementOut(
                code=rule.code,
                title=rule.title,
                icon_url=rule.icon_url,
                description=rule.description,
                obtained_at=ach.created_at.isoformat(),
            )
            for ach, rule in rows
        ]

    # --------------------------------------------------------------
    def _rules(self) -> Iterable[AchievementRule]:
        return self.db.scalars(select(AchievementRule)).all()

    def _already(self, user_id: str) -> set[str]:
        stmt = select(Achievement.code).where(Achievement.user_id == user_id)
        return {row[0] for row in self.db.execute(stmt)}

    def check_and_award(self, user_id: str, events, reply_text: str) -> List[str]:
        unlocked: List[str] = []
        owned = self._already(user_id)

        # rule example: первая встреча → “first_event”
        if events and "first_event" not in owned:
            self.db.add(Achievement(user_id=user_id, code="first_event"))
            unlocked.append("first_event")

        if "спасибо" in reply_text.lower() and "polite" not in owned:
            self.db.add(Achievement(user_id=user_id, code="polite"))
            unlocked.append("polite")

        if unlocked:
            self.db.commit()
            log.info("[Ach] user=%s unlocked=%s", user_id, ",".join(unlocked))
        return unlocked
