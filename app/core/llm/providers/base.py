'''
Базовый интерфейс для LLM-провайдеров.

- Каждый конкретный провайдер (Gemini, OpenAI, Stub и т.п.) обязан
  реализовать два метода:
    - generate()       -> сгенерировать ответ
    - extract_events() -> распарсить события из текста

- Используется client-обёрткой (app/core/llm/client.py) и тестами.
'''

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Sequence

from app.core.llm.schemas import Message, Event


class BaseLLM(ABC):
    """Абстрактный LLM-провайдер."""

    # Уникальное имя провайдера, переопределяется в конкретных классах
    name: str = "base"

    @abstractmethod
    def generate(self, prompt: str, context: Sequence[Message]) -> str:
        """Сгенерировать текст-ответ по prompt + history."""
        raise NotImplementedError  # pragma: no cover

    @abstractmethod
    def extract_events(self, text: str) -> List[Event]:
        """Найти события (дата/время/описание) в сгенерированном тексте."""
        raise NotImplementedError  # pragma: no cover
