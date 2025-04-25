"""
Stub-провайдер для тестов и локальной разработки.
Не обращается к внешним API.
"""

from __future__ import annotations

from typing import List, Sequence

from app.core.llm.schemas import Message, Event
from .base import BaseLLMProvider


class StubLLMProvider(BaseLLMProvider):
    """Минимальный «заглушечный» LLM-клиент."""

    name: str = "stub"

    # возвращаем фиксированную строку, которую ждут unit-тесты
    def generate(self, prompt: str, context: Sequence[Message]) -> str:  # noqa: D401
        return "stub-reply"

    # для тестов calendaring-цепочки можно вернуть пустой список
    def extract_events(self, text: str) -> List[Event]:  # noqa: D401
        return []
