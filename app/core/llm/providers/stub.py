"""In-memory dummy LLM provider for tests/dev."""

from __future__ import annotations

from app.core.llm.message import Message
from .base import BaseLLMProvider


class StubLLMProvider(BaseLLMProvider):
    """Возвращает фиксированные ответы – удобен в unit-тестах."""
    name = "stub"

    def generate(self, prompt: str, ctx: list[Message]) -> str:  # type: ignore[override]
        return "ok"  # тесты ждут именно такой результат

    def extract_events(self, text: str):  # type: ignore[override]
        return []  # ничего не вытаскиваем
