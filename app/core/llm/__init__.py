# app/core/llm/__init__.py
# ──────────────────────────────────────────────────────────
"""Публичный API модуля LLM: фабрика провайдера и типы."""

from app.core.llm.providers.base import (
    Message,
    Event,
    BaseLLM,
    get_llm_provider,
)

# Переименовываем фабрику для удобства внешнего импорта
get_llm = get_llm_provider

__all__ = [
    "Message",
    "Event",
    "BaseLLM",
    "get_llm",
]
