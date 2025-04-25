from __future__ import annotations
 
 import logging
 import re
 from datetime import datetime
 from typing import List
 
 import google.generativeai as genai
 from .base import BaseLLM, Event, Message
 
 from app.config import settings
 from ..base import BaseLLM, Event, Message
 
 log = logging.getLogger(__name__)
 class StubLLM(BaseLLM):
     """Простейший детерминированный провайдер – зелёные тесты."""
 
     def chat(self, user_text: str, ctx: List[Message]):
         reply = "ok"
         events: List[Event] = []
 
 class GeminiLLMProvider(BaseLLM):
     def __init__(self) -> None:  # noqa: D401
         genai.configure(api_key=settings.GEMINI_API_KEY)
         self._model = genai.GenerativeModel("gemini-pro")
         # very naive date like 2025-01-01
         m = re.search(r"(\d{4})-(\d{2})-(\d{2})", user_text)
         if m:
             y, m_, d = map(int, m.groups())
             events.append(Event(title="Detected date", start=datetime(y, m_, d, 12, 0)))
 
     # ------------------------------------------------------------------ #
     def _convert_ctx(self, ctx: List[Message]) -> list[dict]:
         return [{"role": m.role, "content": m.content} for m in ctx]
 
     def generate(self, prompt: str, context: List[Message]) -> str:
         hist = self._convert_ctx(context) + [{"role": "user", "content": prompt}]
         log.info("[LLM] sending prompt to Gemini (%d tokens ctx)", len(hist))
         response = self._model.generate_content(hist)
         reply = response.text.strip()
         log.info("[LLM] got reply len=%d", len(reply))
         return reply
 
     def extract_events(self, text: str) -> List[Event]:
         """
         VERY primitive: ловим «31.12.2025 14:00 текст…».
         В реальном проекте пусть Gemini сделает JSON-парсинг,
         но для MVP и тестов хватит регулярок.
         """
         pattern = re.compile(
             r"(?P<day>\d{1,2})[./](?P<month>\d{1,2})[./](?P<year>\d{4})\s+"
             r"(?P<hour>\d{1,2}):(?P<min>\d{2})\s+(?P<title>.+)",
             re.I,
         )
         m = pattern.search(text)
         if not m:
             return []
 
         dt = datetime(
             int(m["year"]), int(m["month"]), int(m["day"]), int(m["hour"]), int(m["min"])
         )
         return [Event(title=m["title"].strip(), start=dt)]
         return reply, events
