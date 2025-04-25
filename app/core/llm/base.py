# app/core/llm/providers/base.py
# ──────────────────────────────────────────────────────────
"""Базовые типы и абстракция для LLM-провайдеров проекта."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional, TypedDict


# ────────────────────────────────
# Публичные типы, которые импортируют другие модули
# ────────────────────────────────
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


# ────────────────────────────────
# Абстрактный базовый класс LLM-провайдера
# ────────────────────────────────
class BaseLLM(ABC):
    """Интерфейс, который должны реализовывать все провайдеры (Gemini, Stub…)."""

    @abstractmethod
    def generate(
        self,
        prompt: str,
        history: List[Message] | None = None,
    ) -> str:
        """Сгенерировать ответ-реплику (plain-text)."""

    @abstractmethod
    def extract_events(self, text: str) -> List[Event]:
        """Распарсить текст и вернуть список событий (может быть пустым)."""


# ────────────────────────────────
# Функция-фабрика для registry-паттерна
# ────────────────────────────────
from importlib import import_module
from app.config import settings

_PROVIDER_REGISTRY = {
    "gemini": "app.core.llm.providers.gemini:GeminiProvider",
    "stub":   "app.core.llm.providers.stub:StubProvider",
    # при необходимости добавите 'openai', 'llama.cpp' и т.д.
}


def get_llm_provider() -> BaseLLM:
    """
    Возвращает *экземпляр* LLM-провайдера в зависимости от settings.LLM_PROVIDER
    (по умолчанию — «stub» в .env.test).
    """
    provider_path = _PROVIDER_REGISTRY[settings.LLM_PROVIDER]
    module_path, cls_name = provider_path.split(":")

    module = import_module(module_path)
    provider_cls: type[BaseLLM] = getattr(module, cls_name)
    return provider_cls()  # type: ignore[return-value]


# ────────────────────────────────
# Экспортируем имена, чтобы их было видно при `from … import *`
# ────────────────────────────────
__all__ = ["Message", "Event", "BaseLLM", "get_llm_provider"]
