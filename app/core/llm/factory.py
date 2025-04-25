# app/core/llm/factory.py
from app.config import settings
from .gemini import GeminiProvider
from .stub import StubProvider

_LLM = {
    "gemini": GeminiProvider,
    "stub": StubProvider,
}


def get_llm_client():
    """
    Возвращает экземпляр LLM-провайдера согласно settings.LLM_PROVIDER.
    В тестах .env.test выставляет LLM_PROVIDER=stub.
    """
    cls = _LLM.get(settings.LLM_PROVIDER, StubProvider)
    return cls()
