"""
Очень простой провайдер, ничего никуда не ходит —
используется в тестах и дев-режиме без внешних ключей.
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import List

from .shared import parse_dates
from ..base import BaseLLM, Event, Message


class StubLLMProvider(BaseLLM):
    def generate(self, prompt: str, context: List[Message]) -> str:  # noqa: D401
        return "stub-reply"

    def extract_events(self, text: str) -> List[Event]:
        """Ищем примитивно «завтра», «послезавтра» и время формата 12:00."""
        if not (m := re.search(r"(завтра|послезавтра).+?(\d{1,2}:\d{2})", text, re.I)):
            return []

        when_word, time_str = m.groups()
        day_shift = 1 if when_word.lower() == "завтра" else 2
        hour, minute = map(int, time_str.split(":"))
        start_dt = datetime.now().replace(hour=hour, minute=minute, second=0, microsecond=0)
        start_dt += timedelta(days=day_shift)

        return [Event(title="Встреча", start=start_dt)]
