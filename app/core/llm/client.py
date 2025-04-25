# app/core/llm/client.py

from __future__ import annotations

import os
from datetime import datetime
from typing import List

import dateparser.search
import google.generativeai as genai
from pydantic import BaseModel


class Message(BaseModel):
    role: str
    content: str


class Event:
    """
    Тестовый объект-событие, используемый и ожидаемый тестами.
    """
    def __init__(self, title: str, start: datetime):
        self.title = title
        self.start = start               #тесты читают .start
        self.start_dt = start            #наш код читает .start_dt
        self.end_dt = None
        self.metadata = None


class LLMClient:
    """
    Клиент для общения с Google Gemini (Generative AI).
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
            text, languages=["ru", "en"], settings={"PREFER_DATES_FROM": "future"}
        )
        events: list[Event] = []
        if found:
            for snippet, dt in found:
                events.append(Event(title=snippet, start=dt))
        return events
