"""
Базовые типы и абстракция LLM-провайдера.
По этому интерфейсу работают Gemini, Stub и будущие реализации.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, TypedDict


class Message(TypedDict):
    """Сообщение в диалоге."""
    role: str        # 'user' | 'assistant' | …
    content: str     # текст


class Event(TypedDict):
    """Структурированное событие, извлечённое из текста."""
    title: str
    start: str | None          # ISO-строка либо None
    end: str | None            # ISO-строка либо None
    meta: dict | None          # произвольные дополнительные данные


class BaseLLMProvider(ABC):
    """Единый контракт для всех LLM-адаптеров."""

    # ▼------------------- Обязательные методы -------------------▼
    @abstractmethod
    def generate(self, prompt: str, context: List[Message] | None = None) -> str: ...

    @abstractmethod
    def extract_events(self, text: str) -> List[Event]: ...
    # ▲-----------------------------------------------------------▲


# исторический алиас — чтобы старый импорт «BaseLLM» тоже работал
BaseLLM = BaseLLMProvider  # noqa: N816


# ---------------- Фабрика провайдеров ---------------- #
def get_llm_provider(name: str | None = None) -> BaseLLMProvider:
    """
    Возвращает экземпляр провайдера по имени.
    Если имя не передано — смотрим конфиг `settings.LLM_PROVIDER`.
    """
    from app.config import settings  # локальный импорт, чтобы избежать циклов

    provider = (name or settings.LLM_PROVIDER).lower()

    if provider == "stub":
        from .stub import StubLLMProvider
        return StubLLMProvider()
    if provider == "gemini":
        from .gemini import GeminiLLMProvider
        return GeminiLLMProvider()

    raise ValueError(f"Unknown LLM provider: {provider!r}")
