# app/core/llm/client.py
"""
Unified façade, за котором скрывается конкретный провайдер
(Gemini или Stub).  Сам клиент нигде не знает о Google-SDK.
"""

from typing import List

from .schemas import Message, Event
from .factory import get_llm_client


class LLMClient:
    def __init__(self):
        self._impl = get_llm_client()

    # проксируем ↓
    def generate(self, prompt: str, context: List[Message]) -> str:  # noqa: D401
        return self._impl.generate(prompt, context)

    def extract_events(self, text: str) -> List[Event]:
        return self._impl.extract_events(text)
