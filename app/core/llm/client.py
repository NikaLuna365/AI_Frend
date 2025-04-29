# app/core/llm/client.py
from __future__ import annotations # Для использования типов до их объявления

import logging
from typing import List, Sequence # Используем typing для совместимости

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
    Делегирует операции generate/extract_events конкретной асинхронной реализации.
    """
    def __init__(self):
        """
        Инициализирует клиент, получая провайдера через асинхронную фабрику.
        Примечание: Сама фабрика get_llm_provider пока может быть синхронной,
                  но она должна возвращать провайдера с async методами.
        """
        # Фабрика вернет провайдера ('stub', 'gemini', etc.)
        self.provider: BaseLLMProvider = get_llm_provider()
        log.info("LLMClient initialized with provider: %s", self.provider.name)

    async def generate(self, prompt: str, context: Sequence[Message]) -> str:
        """
        Асинхронно генерирует ответ на prompt с учётом истории context.

        Args:
            prompt (str): Основной запрос пользователя.
            context (Sequence[Message]): История диалога (список TypedDict).

        Returns:
            str: Сгенерированный текстовый ответ.
        """
        log.debug(
            "LLMClient generating response via %s provider for prompt: %.50s...",
            self.provider.name, prompt
        )
        # Делегируем вызов асинхронному методу провайдера
        response = await self.provider.generate(prompt, context)
        log.debug("LLMClient received response: %.50s...", response)
        return response

    async def extract_events(self, text: str) -> List[Event]:
        """
        Асинхронно извлекает из текста список событий (даты+описания).

        Args:
            text (str): Текст для анализа.

        Returns:
            List[Event]: Список извлеченных событий (TypedDict).
        """
        log.debug(
            "LLMClient extracting events via %s provider from text: %.50s...",
            self.provider.name, text
        )
        # Делегируем вызов асинхронному методу провайдера
        events = await self.provider.extract_events(text)
        log.debug("LLMClient extracted %d events.", len(events))
        return events

    # Можно добавить другие методы, например, для генерации названий ачивок
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
        """
        log.debug("LLMClient generating achievement name via %s provider...", self.provider.name)
        # Проверяем, есть ли у провайдера такой метод
        if not hasattr(self.provider, 'generate_achievement_name'):
             raise NotImplementedError(
                 f"Provider '{self.provider.name}' does not support 'generate_achievement_name'"
             )
        names = await self.provider.generate_achievement_name(
            context=context,
            style_id=style_id,
            tone_hint=tone_hint,
            style_examples=style_examples
        )
        log.debug("LLMClient received %d achievement names.", len(names))
        return names

    # Аналогично можно добавить метод для генерации иконок, если это делает LLM
    async def generate_achievement_icon(
        self,
        context: str,
        style_id: str,
        style_keywords: str,
        palette_hint: str,
        shape_hint: str
        ) -> bytes: # Возвращаем байты PNG изображения
        """
        Асинхронно генерирует иконку для ачивки (например, через Imagen).

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
        """
        log.debug("LLMClient generating achievement icon via %s provider...", self.provider.name)
        if not hasattr(self.provider, 'generate_achievement_icon'):
            raise NotImplementedError(
                f"Provider '{self.provider.name}' does not support 'generate_achievement_icon'"
            )
        icon_bytes = await self.provider.generate_achievement_icon(
             context=context,
             style_id=style_id,
             style_keywords=style_keywords,
             palette_hint=palette_hint,
             shape_hint=shape_hint
         )
        log.debug("LLMClient received achievement icon (%d bytes).", len(icon_bytes) if icon_bytes else 0)
        return icon_bytes


# Оставляем старые экспорты для совместимости, если нужно, но лучше их убрать позже
# __all__ = ("LLMClient", "Message", "Event")
__all__ = ("LLMClient",) # Экспортируем только клиент
