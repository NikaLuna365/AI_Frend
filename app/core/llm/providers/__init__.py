from __future__ import annotations

from typing import Dict, Type

from app.config import settings
from .base import BaseLLM
from .providers.stub import StubLLM
from .providers.gemini import GeminiLLM

_LLM_REGISTRY: Dict[str, Type[BaseLLM]] = {
    "stub": StubLLM,
    "gemini": GeminiLLM,
}


def get_llm() -> BaseLLM:
    name = settings.LLM_PROVIDER.lower()
    try:
        return _LLM_REGISTRY[name]()  # type: ignore[call-arg]
    except KeyError as exc:  # pragma: no cover
        raise RuntimeError(f"Unknown LLM provider: {name}") from exc
