# app/core/llm/client.py
"""
LLMClient — обёртка над Google Gemini (Generative AI) + тестовый класс Event.
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import List, Any

import dateparser.search
import google.generativeai as genai
from pydantic import BaseModel

# --------------------------------------------------------------------------- #
# Pydantic model для сообщений
# --------------------------------------------------------------------------- #

class Message(BaseModel):
    role: str
    content: str


# --------------------------------------------------------------------------- #
# Тестовый класс Event
# --------------------------------------------------------------------------- #

class Event:
    """
    Объект события, который используют тесты для моков и перехода
    от LLM к календарю.
    """
    def __init__(self, title: str, start: datetime):
        self.title = title
        # Тесты ожидают атрибут .start
        self.start = start
        # Наш код использует .start_dt и .end_dt
        self.start_dt = start
        self.end_dt = None
        self.metadata = None


# --------------------------------------------------------------------------- #
# Клиент
# --------------------------------------------------------------------------- #

class LLMClient:
    """
    Клиент для общения с LLM (Google Gemini).
    """

    def __init__(self) -> None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY env var not set")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel("gemini-pro")

    def generate(self, prompt: str, context: List[Message]) -> str:
        """
        Склеиваем историю + новый промпт, отправляем в модель,
        возвращаем строку ответа.
        """
        hist = [{"role": m.role, "parts": [m.content]} for m in context]
        hist.append({"role": "user", "parts": [prompt]})

        resp = self.model.generate_content(hist)
        return resp.text.strip()

    def extract_events(self, text: str) -> list[Event]:
        """
        Простейший парсер дат → список Event.
        """
        found = dateparser.search.search_dates(
            text,
            languages=["ru", "en"],
            settings={"PREFER_DATES_FROM": "future"},
        )
        events: list[Event] = []
        if found:
            for snippet, dt in found:
                events.append(Event(title=snippet, start=dt))
        return events
