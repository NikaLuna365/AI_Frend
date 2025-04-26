# app/core/llm/providers/stub.py
"""
Stub LLM provider – deterministic & offline.

Нужен для unit-тестов и dev-режима без сетевых вызовов.
"""

from __future__ import annotations

from datetime import datetime
from typing import List

from .base import BaseLLMProvider, Event, Message


class StubLLMProvider(BaseLLMProvider):
    """Returns constant strings; extracts fake date-events via simple heuristics."""

    name = "stub"

    # --------------------------------------------------------------------- #
    #                               Generate                                #
    # --------------------------------------------------------------------- #
    def generate(self, prompt: str, context: List[Message] | None = None) -> str:
        return "stub-reply"

    # --------------------------------------------------------------------- #
    #                           Events extraction                           #
    # --------------------------------------------------------------------- #
    def extract_events(self, text: str) -> List[Event]:
        # extremely naive: look for YYYY-MM-DD and treat it as event.start
        import re

        m = re.search(r"(\d{4})-(\d{2})-(\d{2})", text)
        if not m:
            return []

        year, month, day = map(int, m.groups())
        ev = Event(
            title="Detected date",
            start=datetime(year, month, day, 9, 0),
            end=None,
        )
        return [ev]


__all__: list[str] = ["StubLLMProvider"]
