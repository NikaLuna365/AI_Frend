# app/core/llm/client.py

"""
LLMClient для работы с Google Gemini (Generative AI).
"""

from __future__ import annotations
import os
import importlib
from typing import List, Any

import dateparser.search

import google.generativeai as genai
from google.generativeai import chat as _chat_module

from app.core.llm.schemas import Message

# убедимся, что подмодуль chat доступен
if not hasattr(genai, "chat"):
    genai.chat = _chat_module


class LLMClient:
    """
    Клиент для общения с LLM (Google Gemini).
    """

    def __init__(self) -> None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY not set in environment")
        genai.configure(api_key=api_key)

    def generate(self, prompt: str, context: List[Message]) -> str:
        """
        Отправляем историю + новый prompt в chat-bison-001.
        Возвращаем текст последнего ответа.
        """
        messages_payload = [m.model_dump() for m in context] + [
            Message(role="user", content=prompt).model_dump()
        ]
        resp = genai.chat.create(
            model="models/chat-bison-001",
            prompt={"messages": messages_payload}
        )
        return resp.last

    def extract_events(self, text: str) -> list[Any]:
        """
        Парсим даты в тексте через dateparser.search и возвращаем
        список словарей {title, start_dt, end_dt, metadata}.
        (Здесь можно расширить логику, пока базовый пример.)
        """
        found = dateparser.search.search_dates(text, languages=["ru", "en"])
        events: list[Any] = []
        if found:
            for snippet, dt in found:
                events.append({
                    "title": snippet,
                    "start_dt": dt,
                    "end_dt": None,
                    "metadata": None
                })
        return events
