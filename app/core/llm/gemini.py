# app/core/llm/gemini.py
"""
Реальная обёртка над Google Gemini.
"""

from __future__ import annotations

import os
from typing import List

import google.generativeai as genai

from app.core.llm.schemas import Message, Event
import dateparser.search


class GeminiProvider:
    def __init__(self) -> None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY not set")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel("gemini-pro")

    # ------------------------------------------------------------------ #
    def generate(self, prompt: str, context: List[Message]) -> str:
        hist = [{"role": m.role, "parts": [m.content]} for m in context]
        hist.append({"role": "user", "parts": [prompt]})
        resp = self.model.generate_content(hist)
        return resp.text.strip()

    def extract_events(self, text: str) -> List[Event]:
        found = dateparser.search.search_dates(text, languages=["ru", "en"])
        events: List[Event] = []
        if found:
            for snippet, dt in found:
                events.append(Event(title=snippet, start=dt))
        return events
