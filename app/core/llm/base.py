# app/core/llm/providers/base.py
# ──────────────────────────────────────────────────────────
"""Базовые типы и абстракция для LLM-провайдеров проекта."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional, TypedDict

from app.config import settings  # для фабрики ниже
from importlib import import_module


class Message(TypedDict):
    """Сообщение в чат-истории."""
    role: str         # "user" | "assistant" | "system"
    content: str      # сырой текст


class Event(TypedDict, total=False):
    """Событие, извлечённое из текста пользователями/LLM."""
    title: str
    start: datetime
    end: Optional[datetime]
    description: Optional[str]


class BaseLLM(ABC):
    """Интерфейс, который должны реализовывать все провайдеры (Gemini, Stub…)."""

    @abstractmethod
    def generate(
        self,
        prompt: str,
        history: List[Message] | None = None,
    ) -> str:
        """
        Сгенерировать ответ-реплику (plain-text).
        :param prompt: текущий текст от пользователя
        :param history: список предыдущих сообщений
        :return: текст ответа
        """

    @abstractmethod
    def extract_events(self, text: str) -> List[Event]:
        """
        Распарсить текст и вернуть список событий (может быть пустым).
        :param text: полный текст диалога или сообщение
        :return: список Event
        """


# ──────────────────────────────────────────────────────────
# Registry / фабрика для провайдеров
# ──────────────────────────────────────────────────────────
_PROVIDER_REGISTRY: dict[str, str] = {
    "gemini": "app.core.llm.providers.gemini:GeminiProvider",
    "stub":   "app.core.llm.providers.stub:StubProvider",
    # можно добавить "openai", "llama", и т.д.
}


def get_llm_provider() -> BaseLLM:
    """
    Возвращает экземпляр LLM-провайдера в зависимости от
    settings.LLM_PROVIDER (env: LLM_PROVIDER).
    """
    path = _PROVIDER_REGISTRY.get(settings.LLM_PROVIDER)
    if not path:
        raise RuntimeError(f"Unknown LLM provider: {settings.LLM_PROVIDER!r}")
    module_path, cls_name = path.split(":")
    module = import_module(module_path)
    provider_cls = getattr(module, cls_name)
    return provider_cls()  # type: ignore[return-value]


# Чтобы `from .base import *` работало корректно
__all__ = [
    "Message",
    "Event",
    "BaseLLM",
    "get_llm_provider",
]
