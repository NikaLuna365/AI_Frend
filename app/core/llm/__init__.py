# app/core/llm/__init__.py
from __future__ import annotations

from app.config import settings
from .gemini import GeminiProvider
from .stub import StubProvider

_LLM_REGISTRY = {
    "gemini": GeminiProvider,
    "stub": StubProvider,
}


def get_llm():
    return _LLM_REGISTRY.get(settings.LLM_PROVIDER, StubProvider)()
