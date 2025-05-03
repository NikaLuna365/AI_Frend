# /app/app/core/llm/client.py (Подтвержденная Версия)

from __future__ import annotations

import logging
from typing import List, Sequence

# Импортируем базовые схемы/типы
from .message import Message, Event
# Импортируем асинхронную фабрику провайдеров
from .providers import get_llm_provider
# Импортируем базовый асинхронный интерфейс провайдера для type hinting
from .providers.base import BaseLLMProvider

log = logging.getLogger(__name__)

class LLMClient:
    """
    Асинхронный универсальный клиент для работы с LLM-провайдерами.
    Делегирует операции конкретной асинхронной реализации,
    полученной через фабрику get_llm_provider().
    """
    def __init__(self):
        """
        Инициализирует клиент, получая единственный экземпляр
        провайдера через фабрику.
        """
        # Фабрика вернет закэшированный экземпляр провайдера ('stub', 'gemini', etc.)
        self.provider: BaseLLMProvider = get_llm_provider()
        log.info("LLMClient using provider: %s", self.provider.name)

    async def generate(self, prompt: str, context: Sequence[Message]) -> str:
        """
        Асинхронно генерирует ответ на prompt с учётом истории context.

        Args:
            prompt (str): Основной запрос пользователя.
            context (Sequence[Message]): История диалога.

        Returns:
            str: Сгенерированный текстовый ответ.
        """
        log.debug("LLMClient: Calling provider.generate...")
        response = await self.provider.generate(prompt, context)
        log.debug("LLMClient: Provider.generate returned.")
        return response

    async def extract_events(self, text: str) -> List[Event]:
        """
        Асинхронно извлекает из текста список событий.
        (В текущем MVP провайдер Gemini возвращает пустой список).

        Args:
            text (str): Текст для анализа.

        Returns:
            List[Event]: Список извлеченных событий.
        """
        log.debug("LLMClient: Calling provider.extract_events...")
        events = await self.provider.extract_events(text)
        log.debug("LLMClient: Provider.extract_events returned %d events.", len(events))
        return events

    async def generate_achievement_name(
        self,
        context: str,
        style_id: str,
        tone_hint: str,
        style_examples: str
        ) -> List[str]:
        """
        Асинхронно генерирует названия для ачивок.

        Args:
            context (str): Описание ачивки.
            style_id (str): Идентификатор стиля.
            tone_hint (str): Подсказка по тону.
            style_examples (str): Примеры в нужном стиле.

        Returns:
            List[str]: Список из 3 предложенных названий.

        Raises:
            NotImplementedError: Если метод не реализован в провайдере.
            Exception: При ошибках API.
        """
        log.debug("LLMClient: Calling provider.generate_achievement_name...")
        if not hasattr(self.provider, 'generate_achievement_name'):
             raise NotImplementedError(f"Provider '{self.provider.name}' does not support 'generate_achievement_name'") # pragma: no cover
        names = await self.provider.generate_achievement_name(
            context=context, style_id=style_id, tone_hint=tone_hint, style_examples=style_examples
        )
        log.debug("LLMClient: Provider.generate_achievement_name returned %d names.", len(names))
        return names

    async def generate_achievement_icon(
        self,
        context: str,
        style_id: str,
        style_keywords: str,
        palette_hint: str,
        shape_hint: str
        ) -> bytes:
        """
        Асинхронно генерирует иконку для ачивки.

        Args:
            context (str): Описание ачивки.
            style_id (str): Идентификатор стиля.
            style_keywords (str): Ключевые слова стиля.
            palette_hint (str): Подсказка по палитре.
            shape_hint (str): Подсказка по форме.

        Returns:
            bytes: PNG изображение в виде байтов.

        Raises:
            NotImplementedError: Если метод не реализован в провайдере.
            Exception: При ошибках API.
        """
        log.debug("LLMClient: Calling provider.generate_achievement_icon...")
        if not hasattr(self.provider, 'generate_achievement_icon'):
            raise NotImplementedError(f"Provider '{self.provider.name}' does not support 'generate_achievement_icon'") # pragma: no cover
        icon_bytes = await self.provider.generate_achievement_icon(
             context=context, style_id=style_id, style_keywords=style_keywords, palette_hint=palette_hint, shape_hint=shape_hint
         )
        log.debug("LLMClient: Provider.generate_achievement_icon returned icon.")
        return icon_bytes

# Экспортируем только клиент
__all__ = ("LLMClient",)
