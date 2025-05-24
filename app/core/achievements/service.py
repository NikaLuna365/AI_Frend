# /app/app/core/achievements/service.py (Полная реализация для MVP)

from __future__ import annotations

import logging
from typing import List, Sequence, Optional, Dict, Any # Добавили Dict, Any

from sqlalchemy import select, func as sql_func # Переименовываем func, чтобы не конфликтовать с нашим
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Achievement # Импортируем только Achievement
# LLMClient НЕ НУЖЕН здесь, он используется в Celery задаче

log = logging.getLogger(__name__)

# --- "Зашитые" Правила Ачивок для MVP ---
# Ключ - это achievement_code
# generation_theme - используется как контекст/тема для генерации названия и иконки
HARDCODED_ACHIEVEMENT_RULES: Dict[str, Dict[str, Any]] = {
    "first_message_sent": { # Код ачивки
        "title_hint": "Ice Breaker", # Используется для PENDING статуса
        "generation_theme": "A user sending their very first encouraging message in a new friendly AI chat application, breaking the ice.",
        "description_for_user": "You've sent your first message and started a new friendship!", # Описание для пользователя
        # Условия триггера будут в логике сервиса
    },
    "cat_lover_discovery": {
        "title_hint": "Feline Friend",
        "generation_theme": "A joyful moment of discovering a shared love for cats, perhaps a user mentioning their pet cat.",
        "description_for_user": "You've revealed your love for cats! Meow-tastic!",
        "trigger_keywords": ["cat", "кошка", "котенок", "кот", "кота", "кошку", "котэ", "мур", "мяу"]
    },
    "long_convo_starter": {
        "title_hint": "Chatty Companion",
        "generation_theme": "A user engaging in a significantly long and meaningful conversation with the AI, showing deep engagement.",
        "description_for_user": "Wow, what a great conversation we had! You're a true Chatty Companion.",
        # Триггер может быть по количеству сообщений в сессии или общей истории
    },
    # Добавьте еще 1-2 простых правила для MVP
}

class AchievementsService:
    """
    Сервис для управления логикой достижений (ачивок).
    Определяет, когда выдавать ачивки, создает "ожидающие" записи
    и запускает фоновые задачи для генерации их контента.
    """

    def __init__(self, db_session: AsyncSession):
        """
        Инициализирует сервис.

        Args:
            db_session (AsyncSession): Асинхронная сессия БД.
        """
        self.db: AsyncSession = db_session

    async def _get_achievement(self, user_id: str, achievement_code: str) -> Achievement | None:
        """Вспомогательный метод для получения существующей записи ачивки."""
        stmt = select(Achievement).where(
            Achievement.user_id == user_id,
            Achievement.code == achievement_code
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _create_or_get_pending_achievement(
        self, user_id: str, achievement_code: str, rule_title_hint: str
    ) -> tuple[Achievement, bool]: # Возвращает (ачивку, была_ли_создана_новая_или_сброшена)
        """
        Находит существующую ачивку или создает новую со статусом PENDING_GENERATION.
        Если ачивка уже существует со статусом FAILED_GENERATION, сбрасывает его на PENDING.
        Возвращает саму ачивку и флаг, нужно ли запускать генерацию.
        """
        existing_ach = await self._get_achievement(user_id, achievement_code)
        needs_generation_task = False

        if existing_ach:
            # Ачивка уже есть, проверяем статус
            if existing_ach.status == "COMPLETED":
                log.debug(f"Achievement '{achievement_code}' for user '{user_id}' already COMPLETED.")
                return existing_ach, False # Генерация не нужна
            elif existing_ach.status == "PENDING_GENERATION" or existing_ach.status == "PROCESSING":
                log.debug(f"Achievement '{achievement_code}' for user '{user_id}' already PENDING/PROCESSING.")
                return existing_ach, False # Генерация уже запущена/в процессе
            elif existing_ach.status == "FAILED_GENERATION":
                log.info(f"Retrying FAILED achievement '{achievement_code}' for user '{user_id}'. Setting to PENDING.")
                existing_ach.status = "PENDING_GENERATION"
                existing_ach.title = f"Retrying: {rule_title_hint}" # Обновляем временный титул
                self.db.add(existing_ach)
                needs_generation_task = True
            # Если какой-то другой статус - считаем, что нужно перегенерировать
            else:
                 log.warning(f"Achievement '{achievement_code}' for user '{user_id}' has unusual status '{existing_ach.status}'. Resetting to PENDING.")
                 existing_ach.status = "PENDING_GENERATION"
                 existing_ach.title = f"Resetting: {rule_title_hint}"
                 self.db.add(existing_ach)
                 needs_generation_task = True
            ach_to_process = existing_ach
        else:
            # Ачивки нет, создаем новую PENDING
            log.info(f"Creating new PENDING achievement '{achievement_code}' for user '{user_id}'")
            new_achievement = Achievement(
                user_id=user_id,
                code=achievement_code,
                title=f"Pending: {rule_title_hint}",
                status="PENDING_GENERATION",
            )
            self.db.add(new_achievement)
            ach_to_process = new_achievement
            needs_generation_task = True
        
        if needs_generation_task:
            await self.db.flush() # Получаем ID для новой или применяем изменения для существующей
            if ach_to_process: # Проверка на случай, если flush вернул None (хотя не должен)
                await self.db.refresh(ach_to_process)
        
        return ach_to_process, needs_generation_task


    async def check_and_award(
        self,
        user_id: str,
        message_text: str | None = None, # Для триггеров по ключевым словам
        user_message_count: int = 0, # Для триггера "первое сообщение"
        # Можно добавить другие параметры контекста, например, trigger_event_type
    ) -> List[str]:
        """
        Проверяет условия для "зашитых" правил ачивок и запускает их генерацию.
        Эта функция должна быть вызвана после сохранения сообщения пользователя и ответа AI.

        Args:
            user_id (str): ID пользователя.
            message_text (str | None): Текст последнего сообщения пользователя.
            user_message_count (int): Общее количество сообщений от этого пользователя.

        Returns:
            List[str]: Список кодов ачивок, для которых была ЗАПУЩЕНА фоновая генерация.
        """
        log.debug(f"AchievementsService: Checking achievements for user '{user_id}'")
        triggered_task_codes: List[str] = []
        # Импортируем Celery задачу ВНУТРИ метода, чтобы избежать проблем с импортом при старте
        # и если tasks.py импортирует этот сервис (хотя не должен)
        from app.workers.tasks import generate_achievement_task

        # --- Логика Триггеров для MVP ---
        # Правило 1: "Первое сообщение"
        code = "first_message_sent"
        if code in HARDCODED_ACHIEVEMENT_RULES and user_message_count == 1: # Триггер на первое сообщение
            rule_data = HARDCODED_ACHIEVEMENT_RULES[code]
            achievement, needs_generation = await self._create_or_get_pending_achievement(
                user_id, code, rule_data["title_hint"]
            )
            if needs_generation and achievement:
                generate_achievement_task.delay(
                    user_id=user_id,
                    achievement_code=achievement.code,
                    theme=rule_data["generation_theme"]
                )
                triggered_task_codes.append(achievement.code)

        # Правило 2: "Любитель кошек"
        code = "cat_lover_discovery"
        if message_text and code in HARDCODED_ACHIEVEMENT_RULES:
            rule_data = HARDCODED_ACHIEVEMENT_RULES[code]
            for keyword in rule_data.get("trigger_keywords", []):
                if keyword in message_text.lower():
                    achievement, needs_generation = await self._create_or_get_pending_achievement(
                        user_id, code, rule_data["title_hint"]
                    )
                    if needs_generation and achievement:
                        generate_achievement_task.delay(
                            user_id=user_id,
                            achievement_code=achievement.code,
                            theme=rule_data["generation_theme"]
                        )
                        triggered_task_codes.append(achievement.code)
                        break # Достаточно одного ключевого слова для этого триггера

        # Добавьте другие зашитые правила/триггеры здесь

        if triggered_task_codes:
            # Коммит транзакции (если создавались/обновлялись PENDING записи)
            # будет выполнен FastAPI зависимостью get_async_db_session
            log.info(f"AchievementsService: Tasks dispatched for user '{user_id}': {triggered_task_codes}")
        else:
            log.debug(f"AchievementsService: No new achievements triggered for user '{user_id}'")

        return triggered_task_codes

    async def get_user_achievements(self, user_id: str) -> Sequence[Achievement]:
        """
        Получает список ПОЛНОСТЬЮ СГЕНЕРИРОВАННЫХ (статус COMPLETED) ачивок для пользователя.
        """
        log.debug(f"AchievementsService: Getting COMPLETED achievements for user '{user_id}'")
        stmt = select(Achievement).where(
            Achievement.user_id == user_id,
            Achievement.status == "COMPLETED"
        ).order_by(Achievement.created_at.desc()) # Сначала более новые
        
        result = await self.db.scalars(stmt)
        return result.all()
