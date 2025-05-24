# /app/app/core/achievements/service.py (Версия для MVP - ПОДТВЕРЖДАЕМ)

from __future__ import annotations
import logging
from typing import List, Sequence, Optional, Dict, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func

# --- Импортируем ТОЛЬКО Achievement ---
from .models import Achievement
# -------------------------------------
# from app.core.llm.client import LLMClient # Не нужен здесь, используется в Celery

log = logging.getLogger(__name__)

HARDCODED_ACHIEVEMENT_RULES: Dict[str, Dict[str, Any]] = {
    "first_message": {
        "title_hint": "First Message Sent",
        "generation_theme": "A user sending their very first message in a new friendly chat application.",
    },
    "cat_lover_mention": {
        "title_hint": "Cat Enthusiast",
        "generation_theme": "Expressing a deep love for cats or sharing a cat picture.",
        "trigger_keywords": ["cat", "кошка", "котенок", "кот", "кота", "кошку", "котэ"]
    },
}

class AchievementsService:
    def __init__(self, db_session: AsyncSession):
        self.db: AsyncSession = db_session

    async def _get_achievement(self, user_id: str, code: str) -> Achievement | None:
        stmt = select(Achievement).where(Achievement.user_id == user_id, Achievement.code == code)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _create_pending_achievement(
        self, user_id: str, achievement_code: str, rule_title_hint: str
    ) -> Achievement:
        log.info(f"Creating PENDING achievement '{achievement_code}' for user '{user_id}'")
        new_achievement = Achievement(
            user_id=user_id,
            code=achievement_code,
            title=f"Pending: {rule_title_hint}",
            status="PENDING_GENERATION",
        )
        self.db.add(new_achievement)
        # Не коммитим здесь, коммит будет в check_and_award
        await self.db.flush()
        await self.db.refresh(new_achievement)
        return new_achievement

    async def check_and_award(
        self, user_id: str, message_text: str | None = None
    ) -> List[str]:
        log.debug(f"AchievementsService: Checking achievements for user '{user_id}'")
        triggered_codes_for_generation: List[str] = []
        needs_commit = False

        # Импортируем задачу Celery здесь, чтобы избежать циклических импортов на уровне модуля
        from app.workers.tasks import generate_achievement_task

        for code, rule_data in HARDCODED_ACHIEVEMENT_RULES.items():
            existing_ach = await self._get_achievement(user_id, code)
            should_trigger = False
            if not existing_ach or existing_ach.status == "FAILED_GENERATION": # Позволяем повторную генерацию при FAILED
                # Логика триггера
                if code == "first_message": # Простой триггер - если нет ачивки, значит это первое
                    # Дополнительно можно проверить, что это действительно первое сообщение (например, по истории)
                    # Но для MVP, если ачивки нет - выдаем.
                    should_trigger = True
                elif "trigger_keywords" in rule_data and message_text:
                    for keyword in rule_data["trigger_keywords"]:
                        if keyword in message_text.lower():
                            should_trigger = True
                            break
                # Добавить другие триггеры

            if should_trigger:
                log.info(f"Triggered '{code}' for user '{user_id}'")
                if not existing_ach:
                    pending_ach = await self._create_pending_achievement(user_id, code, rule_data["title_hint"])
                else: # Статус FAILED_GENERATION, используем существующую
                    pending_ach = existing_ach
                    pending_ach.status = "PENDING_GENERATION" # Сбрасываем статус
                    pending_ach.title = f"Retrying: {rule_data['title_hint']}"
                    self.db.add(pending_ach)
                    await self.db.flush()

                generate_achievement_task.delay(
                    user_id=user_id,
                    achievement_code=code,
                    theme=rule_data["generation_theme"]
                )
                triggered_codes_for_generation.append(code)
                needs_commit = True # Если создавали/обновляли PENDING

        if needs_commit:
            await self.db.commit()
            log.info(f"Achievements PENDING records committed for user '{user_id}': {triggered_codes_for_generation}")
        else:
            log.debug(f"No new achievements triggered or PENDING records created for user '{user_id}'")

        return triggered_codes_for_generation

    async def get_user_achievements(self, user_id: str) -> Sequence[Achievement]:
        log.debug(f"AchievementsService: Getting COMPLETED achievements for user '{user_id}'")
        stmt = select(Achievement).where(
            Achievement.user_id == user_id,
            Achievement.status == "COMPLETED"
        ).order_by(Achievement.created_at.desc()) # Сначала новые
        result = await self.db.scalars(stmt)
        return result.all()
