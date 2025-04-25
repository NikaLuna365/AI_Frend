"""
Пакет `providers`: экспорт базовых типов и конкретных реализаций.
Здесь формируем «публичное лицо» для внешнего кода.
"""
from __future__ import annotations

from .base import (                       # noqa: F401  (реэкспорт)
    BaseLLMProvider,
    BaseLLM,          # алиас
    Message,
    Event,
    get_llm_provider,
)

from .stub import StubLLMProvider  # всегда доступен

# Gemini может отсутствовать в dev/CI среде — прячем ImportError
try:
    from .gemini import GeminiLLMProvider
except ImportError:                   # pragma: no cover
    GeminiLLMProvider = None          # type: ignore[assignment]

__all__ = [
    "Message",
    "Event",
    "BaseLLMProvider",
    "BaseLLM",
    "StubLLMProvider",
    "GeminiLLMProvider",
    "get_llm_provider",
]
