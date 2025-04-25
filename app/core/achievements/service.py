# app/core/achievements/service.py
from __future__ import annotations

from datetime import datetime
from typing import List

from sqlalchemy.orm import Session

from app.db.base import get_db_session
from app.core.achievements.models import Achievement, AchievementRule
from app.core.achievements.schemas import AchievementOut
from app.core.llm.schemas import Event


class AchievementsService:
    def __init__(self, db: Session | None = None) -> None:
        # если снаружи не передали сессию, — берём из общего пула
        self.db: Session = db or get_db_session()

    def list_user_achievements(self, user_id: str) -> List[AchievementOut]:
        """
        Возвращает все уже полученные пользователем ачивки,
        отсортированные по дате получения.
        """
        rows = (
            self.db.query(Achievement)
            .filter(Achievement.user_id == user_id)
            .order_by(Achievement.created_at)
            .all()
        )
        # конвертируем ORM-модели в Pydantic-схемы
        return [
            AchievementOut.model_validate(r.__dict__)
            for r in rows
        ]

    # синоним метода
    get_user_achievements = list_user_achievements

    def check_and_award(
        self,
        user_id: str,
        events: list[Event],
        reply_text: str
    ) -> List[AchievementOut]:
        """
        Пробегаем по всем правилам ачивок (AchievementRule),
        проверяем, не удовлетворяет ли своё условие текущее сообщение
        (reply_text) или события events, и если да — выдаём новую ачивку.
        Возвращаем список только что выданных ачивок.
        """
        awarded: List[AchievementOut] = []
        # Загружаем все правила
        rules = self.db.query(AchievementRule).all()

        for rule in rules:
            # здесь должна быть ваша логика проверки условия:
            # пример: если код правила встречается в тексте ответа:
            if rule.code not in reply_text:
                continue

            # проверим, нет ли уже такой ачивки у пользователя
            exists = (
                self.db.query(Achievement)
                .filter(
                    Achievement.user_id == user_id,
                    Achievement.code == rule.code
                )
                .first()
            )
            if exists:
                continue

            # создаём новую запись
            new_ach = Achievement(
                user_id=user_id,
                code=rule.code,
                title=rule.title,
                icon_url=rule.icon_url,
                created_at=datetime.utcnow(),
            )
            self.db.add(new_ach)
            self.db.commit()
            self.db.refresh(new_ach)

            awarded.append(
                AchievementOut.model_validate(new_ach.__dict__)
            )

        return awarded
