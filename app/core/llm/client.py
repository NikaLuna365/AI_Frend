from typing import List
from pydantic import BaseModel
import google.generativeai as genai
from app.config import settings
from datetime import datetime
import dateparser.search

class Message(BaseModel):
    role: str
    content: str

class Event(BaseModel):
    title: str
    start: datetime
    end: datetime | None = None

class LLMClient:
    def __init__(self):
        genai.configure(api_key=settings.GEMINI_API_KEY)

    def generate(self, prompt: str, context: List[Message]) -> str:
        messages = [{"author": msg.role, "content": msg.content} for msg in context]
        messages.append({"author": "user", "content": prompt})
        resp = genai.chat.create(
            model="models/chat-bison-001", temperature=0.7, messages=messages
        )
        return resp.last.text

    def extract_events(self, text: str) -> List[Event]:
        events: List[Event] = []
        # NLP-based date detection
        matches = dateparser.search.search_dates(text, languages=[settings.SPEECH_LANGUAGE.split('-')[0]])
        if matches:
            for phrase, dt in matches:
                # remove trailing punctuation
                title = text.split(phrase)[0].strip().split('.')[-1].strip()
                events.append(Event(title=title or phrase, start=dt))
        # fallback: ISO date patterns
        return events
