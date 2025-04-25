# app/core/llm/client.py
from typing import List, Sequence

from app.core.llm.schemas import Message, Event
from app.core.llm.providers import get_llm_provider


class LLMClient:
    """
    Универсальный клиент для работы с LLM-провайдерами.
    Делегирует операции generate/extract_events конкретной реализации.
    """
    def __init__(self):
        # возьмёт провайдера по имени из settings.LLM_PROVIDER
        self.provider = get_llm_provider()

    def generate(self, prompt: str, context: Sequence[Message]) -> str:
        """
        Сгенерировать ответ на prompt с учётом истории context.
        """
        return self.provider.generate(prompt, context)

    def extract_events(self, text: str) -> List[Event]:
        """
        Извлечь из текста список событий (даты+описания).
        """
        return self.provider.extract_events(text)


# Т.к. в старых тестах импортировали Message и Event прямо из client.py,
# экспортируем их здесь
__all__ = ("LLMClient", "Message", "Event")
