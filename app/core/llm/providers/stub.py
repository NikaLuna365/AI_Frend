from __future__ import annotations

import re
from datetime import datetime
from typing import List

from .base import BaseLLM, Event, Message


class StubLLM(BaseLLM):
    """Простейший детерминированный провайдер – зелёные тесты."""

    def chat(self, user_text: str, ctx: List[Message]):
        reply = "ok"
        events: List[Event] = []

        # very naive date like 2025-01-01
        m = re.search(r"(\d{4})-(\d{2})-(\d{2})", user_text)
        if m:
            y, m_, d = map(int, m.groups())
            events.append(Event(title="Detected date", start=datetime(y, m_, d, 12, 0)))

        return reply, events
