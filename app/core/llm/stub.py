# app/core/llm/stub.py
"""
Заглушка LLM для unit-тестов (не ходит во внешние API).
"""

from datetime import datetime
from typing import List

from .schemas import Message, Event


class StubProvider:
    def generate(self, prompt: str, context: List[Message]) -> str:
        return "stub-reply"

    def extract_events(self, text: str) -> List[Event]:
        # простая фиксация на «завтра»
        tomorrow = datetime.utcnow().replace(hour=9, minute=0, second=0, microsecond=0)
        return [Event(title="Stub event", start=tomorrow)]
