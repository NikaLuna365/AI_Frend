# app/core/llm/client.py
"""
LLMClient — обёртка над Google Gemini (Generative AI).
Работает и в проде, и в тестах (там методы обычно мокируются).
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import List, Any

import dateparser.search
import google.generativeai as genai
from pydantic import BaseModel

# --------------------------------------------------------------------------- #
# Pydantic model для истории
# --------------------------------------------------------------------------- #

class Message(BaseModel):
    role: str
    content: str


# --------------------------------------------------------------------------- #
# Клиент
# --------------------------------------------------------------------------- #

class LLMClient:
    def __init__(self) -> None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY env var not set")
        genai.configure(api_key=api_key)
        # gemini-pro — универсальная модель чата
        self.model = genai.GenerativeModel("gemini-pro")

    # ----------------- публичные методы ----------------- #

    def generate(self, prompt: str, context: List[Message]) -> str:
        """
        Склеиваем историю + новый промпт, отправляем в модель,
        возвращаем строку ответа.
        """
        # Gemini принимает список dict(role=…, parts=[…])
        hist = [
            {"role": m.role, "parts": [m.content]}
            for m in context
        ] + [{"role": "user", "parts": [prompt]}]

        resp = self.model.generate_content(hist)
        # resp.text — готовый ответ
        return resp.text.strip()

    def extract_events(self, text: str) -> list[dict[str, Any]]:
        """
        Простейший парсер дат → список словарей
        (title/start_dt); расширяйте при желании.
        """
        found = dateparser.search.search_dates(
            text, languages=["ru", "en"], settings={"PREFER_DATES_FROM": "future"}
        )
        events: list[dict[str, Any]] = []
        if found:
            for snippet, dt in found:
                events.append(
                    {
                        "title": snippet,
                        "start_dt": dt,
                        "end_dt": None,
                        "metadata": None,
                    }
                )
        return events
