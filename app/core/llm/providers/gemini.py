from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import List

import google.generativeai as genai

from app.config import settings
from .base import BaseLLM, Event, Message

log = logging.getLogger(__name__)

genai.configure(api_key=settings.GEMINI_API_KEY)


class GeminiLLM(BaseLLM):
    def __init__(self) -> None:  # noqa: D401
        self._model = genai.GenerativeModel("gemini-pro")

    # -----------------------------------------------------------------
    def chat(self, user_text: str, ctx: List[Message]):
        hist = [{"role": m.role, "parts": [m.content]} for m in ctx]
        hist.append({"role": "user", "parts": [user_text]})

        resp = self._model.generate_content(hist)
        reply = resp.text

        events: List[Event] = []
        m = re.search(r"(\d{4})-(\d{2})-(\d{2})", user_text)
        if m:
            y, m_, d = map(int, m.groups())
            events.append(Event(title="Event from gemini", start=datetime(y, m_, d, 9, 0)))

        return reply, events
