# /app/app/core/achievements/service.py (Версия для MVP с зашитыми правилами)

from __future__ import annotations

import logging
from typing import List, Sequence, Optional, Dict, Any # Добавили Dict, Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func

# --- ИСПРАВЛЕНИЕ: Импортируем ТОЛЬКО Achievement ---
from .models import Achievement
# ----------------------------------------------
# from app.core.llm.client import LLMClient # LLMClient теперь используется в Celery задаче

log = logging.getLogger(__name__)

# --- Пример "зашитых" правил для MVP ---
# Ключ - это achievement_code
HARDCODED_ACHIEVEMENT_RULES: Dict[str, Dict[str, Any]] = {
    "first_message": {
        "title_hint": "First Message Sent", # Подсказка для пользователя/лога
        "generation_theme": "A user sending their very first message in a new friendly chat application.",
        "trigger_description": "Awarded for sending the first message."
    },
    "cat_lover_mention": {
        "title_hint": "Cat Lover Mention",
        "generation_theme": "Expressing love for cats or mentioning a pet cat.",
        "trigger_keywords": ["cat", "кошка", "котенок", "кот", "кота", "кошку"]
    },
    # Добавьте другие правила по мере необходимости
}
# ---------------------------------------

class AchievementsService:
    def __init__(self, db_session: AsyncSession): # Убрали llm_client
        self.db: AsyncSession = db_session
        # self.llm: LLMClient = llm_client # LLMClient теперь в Celery задаче

    async def _get_achievement(self, user_id: str, code: str) -> Achievement | None:
        """Вспомогательный метод для получения существующей ачивки."""
        stmt = select(Achievement).where(Achievement.user_id == user_id, Achievement.code == code)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _create_pending_achievement(
        self, user_id: str, achievement_code: str, rule_title_hint: str
    ) -> Achievement:
        """Создает новую запись ачивки со статусом PENDING_GENERATION."""
        log.info(f"Creating PENDING achievement '{achievement_code}' for user '{user_id}'")
        new_achievement = Achievement(
            user_id=user_id,
            code=achievement_code,
            title=f"Pending: {rule_title_hint}", # Временный заголовок
            status="PENDING_GENERATION",
            badge_png_url=None
        )
        self.db.add(new_achievement)
        await self.db.flush() # Получаем ID
        await self.db.refresh(new_achievement)
        return new_achievement

    async def check_and_award(
        self,
        user_id: str,
        message_text: str | None = None, # Основной триггер для MVP
        # trigger_context: Any = None # Более общий контекст, если понадобится
    ) -> List[str]: # Возвращает список кодов запущенных на генерацию ачивок
        """
        Проверяет условия для "зашитых" правил и запускает генерацию ачивок.
        """
        log.debug(f"AchievementsService: Checking achievements for user '{user_id}'")
        triggered_codes_for_generation: List[str] = []

        from app.workers.tasks import generate_achievement_task # Импорт Celery задачи

        # 1. Правило "Первое сообщение"
        first_message_code = "first_message"
        if first_message_code in HARDCODED_ACHIEVEMENT_RULES:
            existing_fm_ach = await self._get_achievement(user_id, first_message_code)
            if not existing_fm_ach: # Если ачивки еще нет
                log.info(f"Triggered '{first_message_code}' for user '{user_id}'")
                rule_data = HARDCODED_ACHIEVEMENT_RULES[first_message_code]
                pending_ach = await self._create_pending_achievement(user_id, first_message_code, rule_data["title_hint"])
                generate_achievement_task.delay(
                    user_id=user_id,
                    achievement_code=first_message_code,
                    theme=rule_data["generation_theme"]
                )
                triggered_codes_for_generation.append(first_message_code)

        # 2. Правило "Упоминание кошек" (пример)
        cat_lover_code = "cat_lover_mention"
        if message_text and cat_lover_code in HARDCODED_ACHIEVEMENT_RULES:
            rule_data = HARDCODED_ACHIEVEMENT_RULES[cat_lover_code]
            for keyword in rule_data.get("trigger_keywords", []):
                if keyword in message_text.lower():
                    existing_cl_ach = await self._get_achievement(user_id, cat_lover_code)
                    if not existing_cl_ach:
                        log.info(f"Triggered '{cat_lover_code}' for user '{user_id}' by keyword '{keyword}'")
                        pending_ach_cl = await self._create_pending_achievement(user_id, cat_lover_code, rule_data["title_hint"])
                        generate_achievement_task.delay(
                            user_id=user_id,
                            achievement_code=cat_lover_code,
                            theme=rule_data["generation_theme"]
                        )
                        triggered_codes_for_generation.append(cat_lover_code)
                        break # Достаточно одного ключевого слова

        # Добавьте другие "зашитые" правила здесь

        if triggered_codes_for_generation:
            await self.db.commit() # Коммитим создание PENDING ачивок
            log.info(f"Achievements generation tasked for user '{user_id}': {triggered_codes_for_generation}")
        else:
            log.debug(f"No new achievements triggered for user '{user_id}'")

        return triggered_codes_for_generation

    async def get_user_achievements(self, user_id: str) -> Sequence[Achievement]:
        """Получает список ПОЛНОСТЬЮ СГЕНЕРИРОВАННЫХ ачивок для пользователя."""
        log.debug(f"AchievementsService: Getting COMPLETED achievements for user '{user_id}'")
        stmt = select(Achievement).where(
            Achievement.user_id == user_id,
            Achievement.status == "COMPLETED" # Показываем только завершенные
        ).order_by(Achievement.created_at)
        result = await self.db.scalars(stmt)
        return result.all()
