"""
Registry-фабрика LLM-провайдеров.

Используйте:
    from app.core.llm.providers import get_llm_provider
    prov = get_llm_provider()          # из settings.LLM_PROVIDER
    prov = get_llm_provider("stub")    # явно

Провайдеры должны наследовать BaseLLMProvider
и регистрироваться в ``_PROVIDERS`` ниже.
"""

from __future__ import annotations

from typing import Dict, Type

from app.config import settings
from .base import BaseLLMProvider
from .stub import StubLLMProvider

# Здесь регистрируются все реализации
_PROVIDERS: Dict[str, Type[BaseLLMProvider]] = {
    StubLLMProvider.name: StubLLMProvider,
    # 'gemini': GeminiLLMProvider,   # добавите позже
    # 'openai': OpenAILLMProvider,
}


# ────────────────────────────────────────────────
# Фабрика-доступ
# ────────────────────────────────────────────────
def get_llm_provider(name: str | None = None) -> BaseLLMProvider:
    """
    Вернуть инстанс провайдера по имени.

    Если имя не передано, берётся из settings.LLM_PROVIDER.
    """
    provider_name = (name or settings.LLM_PROVIDER or "stub").lower()
    try:
        return _PROVIDERS[provider_name]()  # type: ignore[call-arg]
    except KeyError as exc:  # pragma: no cover
        raise ValueError(
            f"LLM provider '{provider_name}' не зарегистрирован. "
            f"Доступно: {list(_PROVIDERS)}"
        ) from exc


# Что экспортируем наружу
__all__ = (
    "BaseLLMProvider",
    "StubLLMProvider",
    "get_llm_provider",
)
