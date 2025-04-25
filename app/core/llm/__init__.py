"""
Верхнеуровневый модуль `app.core.llm`.

* Экспортирует базовые типы (`Message`, `Event`).
* Предоставляет фабрику `get_llm`, которая возвращает готовый LLM-провайдер
  в соответствии с настройкой `settings.LLM_PROVIDER`.
"""
from __future__ import annotations

from app.core.llm.providers import (   # noqa: F401
    Message,
    Event,
    BaseLLMProvider,
    get_llm_provider,
)

# Наружу отдаём короткое имя, как раньше требовали импорты:
get_llm = get_llm_provider  # noqa: N816

__all__ = ["get_llm", "BaseLLM", "Event", "Message", "StubLLMProvider", "GeminiLLMProvider"]
