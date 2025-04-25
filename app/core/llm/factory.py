# app/core/llm/factory.py
"""
Фабрика LLM-клиентов.
"""

from app.config import settings
from .gemini import GeminiProvider
from .stub import StubProvider

_LLM_PROVIDERS = {
    "gemini": GeminiProvider,
    "stub": StubProvider,
}

def get_llm_client():
    cls = _LLM_PROVIDERS.get(settings.LLM_PROVIDER, StubProvider)
    return cls()
