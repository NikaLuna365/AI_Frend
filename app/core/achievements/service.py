# app/core/achievements/service.py

from __future__ import annotations

import logging
from typing import List, Sequence # Добавим Sequence

# --- SQLAlchemy и Сессия ---
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
# --- НЕ ИМПОРТИРУЕМ get_db_session ---
# Вместо этого, сервис будет получать AsyncSession через __init__

# --- Модели ---
from .models import AchievementRule, Achievement # Предполагаем, что модели здесь
from app.core.llm.message import Event # Для информации о событии

# --- LLM Клиент ---
# Предполжим, что у нас есть способ получить LLMClient,
# возможно, через фабрику или DI позже. Пока импортируем.
from app.core.llm.client import LLMClient

# --- Хранилище Файлов ---
# TODO: Добавить интеграцию с хранилищем файлов (S3/GCS)

log = logging.getLogger(__name__)

class AchievementsService:
    """
    Асинхронный сервис для управления Достижениями (Ачивками).

    - Проверяет условия выполнения правил ачивок.
    - Генерирует названия и иконки через LLM (асинхронно).
    - Сохраняет разблокированные ачивки в БД.
    - Загружает иконки в хранилище файлов.
    """

    def __init__(self, db_session: AsyncSession, llm_client: LLMClient):
        """
        Инициализирует сервис.

        Args:
            db_session (AsyncSession): Асинхронная сессия БД.
            llm_client (LLMClient): Асинхронный клиент для LLM.
        """
        self.db: AsyncSession = db_session
        self.llm: LLMClient = llm_client
        # TODO: Инициализировать клиент для хранилища файлов

    async def _get_rule(self, code: str) -> AchievementRule | None:
        """Вспомогательный метод для получения правила по коду."""
        stmt = select(AchievementRule).where(AchievementRule.code == code)
        result = await self.db.scalars(stmt)
        return result.first()

    async def _has_achievement(self, user_id: str, code: str) -> bool:
        """Проверяет, есть ли у пользователя уже такая ачивка."""
        stmt = select(Achievement.id).where(
            Achievement.user_id == user_id,
            Achievement.code == code
        ).limit(1)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def check_and_award(
        self,
        user_id: str,
        events: List[Event] | None = None, # События из LLM
        reply_text: str | None = None, # Ответ LLM
        # Можно добавить другие контекстные данные: message, reminder, etc.
        trigger_key: str | None = None # Явный ключ триггера (напр., "message_sent")
    ) -> List[str]:
        """
        Проверяет условия выполнения ачивок и выдает новые.
        Основная точка входа для выдачи ачивок.

        Args:
            user_id (str): ID пользователя.
            events (List[Event] | None, optional): События, распознанные LLM.
            reply_text (str | None, optional): Текст ответа LLM.
            trigger_key (str | None, optional): Явный ключ события-триггера.

        Returns:
            List[str]: Список кодов newly unlocked ачивок.
        """
        log.debug("Checking achievements for user %s (trigger: %s)", user_id, trigger_key)
        unlocked_codes: List[str] = []

        # --- Логика определения, какие ачивки проверить ---
        # TODO: Реализовать сложную логику на основе trigger_key, events, reply_text
        # и, возможно, состояния пользователя (статистики и т.д.)
        # Сейчас для примера проверим ачивку 'first_event', если пришли события
        codes_to_check: List[str] = []
        if events:
            codes_to_check.append("first_event") # Пример правила
        if trigger_key == "message_saved":
            codes_to_check.append("first_message") # Другой пример
        # Добавить другие правила...

        # --- Проверка и выдача ---
        for code in set(codes_to_check): # Используем set для уникальности
            if not await self._has_achievement(user_id, code):
                log.info("Checking rule '%s' for user %s", code, user_id)
                rule = await self._get_rule(code)
                if rule:
                    # TODO: Добавить более сложную проверку условий правила, если нужно
                    log.info("Rule '%s' met! Awarding achievement to user %s.", code, user_id)
                    try:
                        await self._award_achievement(user_id, rule)
                        unlocked_codes.append(code)
                    except Exception as e:
                        log.exception(
                            "Failed to award achievement '%s' to user %s: %s",
                            code, user_id, e
                        )
                        # Не прерываем процесс из-за ошибки с одной ачивкой
                else:
                    log.warning("Achievement rule with code '%s' not found in DB.", code)

        if unlocked_codes:
            log.info("User %s unlocked new achievements: %s", user_id, unlocked_codes)

        # Возвращаем только коды новых ачивок
        return unlocked_codes

    async def _award_achievement(self, user_id: str, rule: AchievementRule):
        """
        Внутренний метод для генерации и сохранения конкретной ачивки.

        Args:
            user_id (str): ID пользователя.
            rule (AchievementRule): Правило ачивки для выдачи.

        Raises:
            Exception: При ошибках генерации или сохранения.
        """
        # --- Генерация контента (вынести в Celery?) ---
        # TODO: Определить параметры для генерации (стиль, палитра и т.д.)
        # на основе правила (rule) или настроек пользователя/системы.
        style_id = "cartoon_absurd" # Пример
        # ... другие параметры ...

        # Генерируем название (пример)
        generated_names = ["Temporary Name 1", "Temporary Name 2", "Temporary Name 3"] # Заглушка
        # TODO: Заменить на реальный вызов LLM
        # generated_names = await self.llm.generate_achievement_name(...)
        achievement_title = generated_names[0] # TODO: Добавить проверку уникальности имени

        # Генерируем иконку (пример)
        icon_bytes = b"fake-png-bytes" # Заглушка
        # TODO: Заменить на реальный вызов LLM
        # icon_bytes = await self.llm.generate_achievement_icon(...)

        # --- Сохранение иконки (вынести в Celery?) ---
        icon_url = None
        if icon_bytes:
             # TODO: Реализовать загрузку в S3/GCS и получение URL
             # storage_client = get_storage_client()
             # icon_url = await storage_client.upload(
             #    f"achievements/{user_id}/{rule.code}.png", icon_bytes
             # )
             icon_url = f"http://example.com/achievements/{rule.code}.png" # Заглушка URL
             log.info("Generated icon for achievement '%s', URL: %s", rule.code, icon_url)


        # --- Сохранение ачивки в БД ---
        new_achievement = Achievement(
            user_id=user_id,
            code=rule.code,
            # Денормализуем поля из правила
            title=achievement_title, # Используем сгенерированное название
            icon_url=icon_url, # Используем URL из хранилища
        )
        self.db.add(new_achievement)
        await self.db.flush() # Достаточно flush, коммит будет снаружи
        log.info("Saved achievement record for user %s, code '%s'", user_id, rule.code)

    async def get_user_achievements(self, user_id: str) -> Sequence[Achievement]:
        """
        Получает список разблокированных ачивок для пользователя.

        Args:
            user_id (str): ID пользователя.

        Returns:
            Sequence[Achievement]: Список объектов Achievement.
        """
        log.debug("Getting achievements for user %s", user_id)
        stmt = select(Achievement).where(Achievement.user_id == user_id).order_by(Achievement.created_at)
        result = await self.db.scalars(stmt)
        achievements = result.all()
        log.debug("Found %d achievements for user %s", len(achievements), user_id)
        return achievements
