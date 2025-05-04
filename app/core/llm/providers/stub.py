# /app/app/core/llm/providers/stub.py (Добавляем заглушку generate_achievement_icon)

from __future__ import annotations
import logging # Добавляем logging
from typing import List, Sequence, Optional # Добавляем Optional

from app.core.llm.message import Message, Event
from .base import BaseLLMProvider

log = logging.getLogger(__name__)

class StubLLMProvider(BaseLLMProvider):
    """Возвращает фиксированные ответы – удобен в unit-тестах."""
    name = "stub"

    async def generate(self, prompt: str, ctx: Sequence[Message]) -> str:
        log.debug("StubLLMProvider: generate called")
        return "ok" # Для тестов API чата

    async def extract_events(self, text: str) -> List[Event]:
        log.debug("StubLLMProvider: extract_events called")
        return [] # Ничего не извлекаем

    async def generate_achievement_name(
        self, context: str, style_id: str, tone_hint: str, style_examples: str
    ) -> List[str]:
        log.debug("StubLLMProvider: generate_achievement_name called")
        return ["Stub Name One", "Stub Name Two", "Stub Name Three"]

    # --- НОВАЯ ЗАГЛУШКА МЕТОДА ---
    async def generate_achievement_icon(
        self, context: str, style_id: str, style_keywords: str,
        palette_hint: str, shape_hint: str
        ) -> bytes | None:
        log.debug("StubLLMProvider: generate_achievement_icon called (returns None)")
        # В тестах обычно не нужна реальная генерация, возвращаем None
        # или можно вернуть заранее подготовленные тестовые байты PNG.
        return None
    # ---------------------------
