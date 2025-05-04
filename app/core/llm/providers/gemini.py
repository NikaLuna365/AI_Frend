# /app/app/core/llm/providers/gemini.py (ФИНАЛЬНАЯ ИСПРАВЛЕННАЯ ВЕРСИЯ v3)

from __future__ import annotations

import logging
import google.generativeai as genai
from google.generativeai.types import GenerationConfig # Убираем SafetySetting, HarmCategory
from typing import List, Sequence, Optional, Dict, Any

from .base import BaseLLMProvider, Message, Event
from app.config import settings

log = logging.getLogger(__name__)

# Проверка конфигурации SDK
try:
    _test_model = genai.GenerativeModel('gemini-1.5-flash-latest')
    log.info("Google Generative AI SDK seems configured correctly.")
except Exception as e:
    log.exception("Failed to initialize/configure Google Generative AI SDK: %s", e)

# Системный Промпт
SYSTEM_PROMPT_AI_FRIEND = """
You are AI-Friend, a personalized AI companion... (Полный текст)
"""

class GeminiLLMProvider(BaseLLMProvider):
    name = "gemini"
    DEFAULT_MODEL_NAME = "gemini-1.5-flash-latest"
    DEFAULT_SAFETY_SETTINGS = [ # Определяем как список словарей
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    ]

    def __init__(self, model_name: Optional[str] = None) -> None:
        self.model_name = model_name or self.DEFAULT_MODEL_NAME
        self.system_prompt = SYSTEM_PROMPT_AI_FRIEND
        try:
            # --- ИСПРАВЛЕНИЕ: Убираем system_instruction из инициализации ---
            self.model = genai.GenerativeModel(
                model_name=self.model_name
                # БЕЗ system_instruction здесь
            )
            # ---------------------------------------------------------------
            self.generation_config = GenerationConfig(temperature=0.7, candidate_count=1)
            log.info("GeminiLLMProvider initialized with model: %s", self.model_name)
        except Exception as e:
            log.exception("Failed to initialize GenerativeModel '%s': %s", self.model_name, e)
            raise RuntimeError(f"Failed to initialize Gemini model {self.model_name}") from e

    def _prepare_gemini_history(self, context: Sequence[Message], current_prompt: Optional[str] = None) -> List[Dict[str, Any]]:
        # ... (код без изменений) ...
        gemini_history = []
        for msg in context:
            content = msg.get("content", "").strip();
            if not content: continue
            role = "model" if msg.get("role") == "assistant" else "user"
            gemini_history.append({'role': role, 'parts': [content]})
        if current_prompt:
             gemini_history.append({'role': 'user', 'parts': [current_prompt]})
        return gemini_history

    async def generate(
        self, prompt: str, context: Sequence[Message],
        rag_facts: Optional[List[str]] = None, system_prompt_override: Optional[str] = None
    ) -> str:
        log.debug("Gemini: Generating response...")
        gemini_history = self._prepare_gemini_history(context, None) # Готовим историю БЕЗ последнего промпта

        if rag_facts:
            facts_text = "\n".join(f"- {fact}" for fact in rag_facts)
            rag_message = {'role': 'user', 'parts': [f"(Context: Remember these facts about the user:\n{facts_text}\n)"]}
            gemini_history.append(rag_message) # Добавляем факты перед промптом
            log.debug("Gemini: Added %d RAG facts.", len(rag_facts))

        # Добавляем последний промпт пользователя в конец подготовленной истории
        gemini_history.append({'role': 'user', 'parts': [prompt]})

        system_instruction = system_prompt_override or self.system_prompt

        try:
            # --- ИСПРАВЛЕНИЕ: ДОБАВЛЯЕМ system_instruction сюда ---
            response = await self.model.generate_content_async(
                contents=gemini_history,
                generation_config=self.generation_config,
                safety_settings=self.DEFAULT_SAFETY_SETTINGS,
                # Передаем системную инструкцию как аргумент generate_content_async
                system_instruction=system_instruction # <-- ДОБАВЛЕНО СЮДА
            )
            # -----------------------------------------------------

            # --- Обработка ответа (без изменений) ---
            if response and response.text:
                return response.text.strip()
            else:
                # ... (обработка пустых/заблокированных) ...
                reason = "Unknown reason"; # ... (логика определения reason) ...
                log.warning("Gemini returned empty/blocked response. Reason: %s", reason)
                return f"(Я не могу сгенерировать ответ сейчас. Причина: {reason})"

        except Exception as e:
            log.exception("Error during Gemini API call in generate(): %s", e)
            return f"(Произошла ошибка при обращении к AI: {type(e).__name__})"

    # --- Метод generate_achievement_name (исправляем аналогично) ---
    async def generate_achievement_name(
        self, context: str, style_id: str, tone_hint: str, style_examples: str
    ) -> List[str]:
        log.debug("Gemini: Generating achievement name...")
        # --- Промпт для названий (без изменений) ---
        system_prompt = "You are a highly creative naming expert..."
        user_prompt = f""" ... """
        full_prompt_contents = [ {'role': 'user', 'parts': [system_prompt]}, ...]
        # ---------------------------------------------
        try:
            generation_config_names = GenerationConfig(temperature=0.8, candidate_count=1)
            # --- ИСПРАВЛЕНИЕ: Убираем system_instruction отсюда (он в промпте) ---
            response = await self.model.generate_content_async(
                contents=full_prompt_contents,
                generation_config=generation_config_names,
                safety_settings=self.DEFAULT_SAFETY_SETTINGS
                # system_instruction НЕ нужен, т.к. роль system есть в contents
            )
            # ----------------------------------------------------------
            # --- Обработка ответа (без изменений) ---
            if response and response.text:
                # ... (парсинг имен) ...
                return valid_names
            else:
                # ... (обработка пустых/заблокированных) ...
                return ["Default Name 1", "Default Name 2", "Default Name 3"]
        except Exception as e:
            log.exception(...)
            return ["Default Name 1", "Default Name 2", "Default Name 3"]

    async def extract_events(self, text: str) -> List[Event]: return []

__all__ = ["GeminiLLMProvider"]
