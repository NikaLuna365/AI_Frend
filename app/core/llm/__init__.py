"""
core.llm
~~~~~~~~
Адаптивный слой поверх конкретных LLM-SDK.

Интерфейс:
    class BaseLLM:
        def generate(self, prompt: str, context: list[Message]) -> str: ...
        def extract_events(self, text: str) -> list[Event]: ...

Фабрика:
    from app.core.llm import get_llm
    llm = get_llm()        # выбирает нужный класс по settings.LLM_PROVIDER
"""
from __future__ import annotations

from typing import Dict, Type

from app.config import settings
from .base import BaseLLM
from .providers.stub import StubLLMProvider
from .providers.gemini import GeminiLLMProvider

# ────────────────────────────────────────────────────────────
#   РЕЕСТР
# ────────────────────────────────────────────────────────────
_LLM_REGISTRY: Dict[str, Type[BaseLLM]] = {
    "stub": StubLLMProvider,
    "gemini": GeminiLLMProvider,
}


def get_llm() -> BaseLLM:
    """Возвращает инстанс нужного провайдера согласно конфигу."""
    provider = settings.LLM_PROVIDER.lower()
    try:
        return _LLM_REGISTRY[provider]()  # type: ignore[call-arg]
    except KeyError as exc:  # pragma: no cover
        raise RuntimeError(f"Unknown LLM provider: {provider}") from exc
