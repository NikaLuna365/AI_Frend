# /app/app/core/llm/providers/gemini.py (Финальная Исправленная Версия v2)

from __future__ import annotations

import logging
import google.generativeai as genai
# Убираем ненужные импорты Safety*
from google.generativeai.types import GenerationConfig
from typing import List, Sequence, Optional, Dict, Any

from .base import BaseLLMProvider, Message, Event
from app.config import settings

log = logging.getLogger(__name__)

# Проверка конфигурации SDK (оставляем)
try:
    _test_model = genai.GenerativeModel('gemini-1.5-flash-latest')
    log.info("Google Generative AI SDK seems configured correctly.")
except Exception as e:
    log.exception("Failed to initialize/configure Google Generative AI SDK: %s", e)

# Системный Промпт (оставляем)
SYSTEM_PROMPT_AI_FRIEND = """
You are AI-Friend... (Полный текст)
"""

class GeminiLLMProvider(BaseLLMProvider):
    name = "gemini"
    DEFAULT_MODEL_NAME = "gemini-1.5-flash-latest"
    DEFAULT_SAFETY_SETTINGS = [
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    ]

    def __init__(self, model_name: Optional[str] = None) -> None:
        self.model_name = model_name or self.DEFAULT_MODEL_NAME
        self.system_prompt = SYSTEM_PROMPT_AI_FRIEND # Сохраняем для удобства
        try:
            # --- ИСПРАВЛЕНИЕ: Передаем system_instruction ЗДЕСЬ ---
            self.model = genai.GenerativeModel(
                model_name=self.model_name,
                # Передаем системный промпт при инициализации модели
                system_instruction=self.system_prompt
                # safety_settings здесь передавать не нужно, передаем в generate_content
            )
            # ---------------------------------------------------
            self.generation_config = GenerationConfig(
                temperature=0.7,
                candidate_count=1,
            )
            log.info(
                "GeminiLLMProvider initialized with model: %s and system prompt.",
                self.model_name
            )
        except Exception as e:
            log.exception(...) # Оставляем обработку ошибки
            raise RuntimeError(...) from e

    # --- Функция _prepare_gemini_history (оставляем как есть) ---
    def _prepare_gemini_history(self, context: Sequence[Message], current_prompt: Optional[str] = None) -> List[Dict[str, Any]]:
        # ... (код без изменений) ...
        gemini_history = []
        for msg in context:
            content = msg.get("content", "").strip()
            if not content: continue
            role = "model" if msg.get("role") == "assistant" else "user"
            gemini_history.append({'role': role, 'parts': [content]})
        if current_prompt:
             gemini_history.append({'role': 'user', 'parts': [current_prompt]})
        return gemini_history


    async def generate(
        self,
        prompt: str,
        context: Sequence[Message],
        rag_facts: Optional[List[str]] = None,
        system_prompt_override: Optional[str] = None # Эта опция теперь не будет работать напрямую
        ) -> str:
        log.debug("Gemini: Generating response...")

        # --- Подготовка Контекста ---
        gemini_history = self._prepare_gemini_history(context, prompt)
        if rag_facts:
            # ... (код добавления RAG фактов без изменений) ...
            facts_text = "\n".join(f"- {fact}" for fact in rag_facts)
            rag_message = {'role': 'user', 'parts': [f"(Вспомни эти факты о пользователе:\n{facts_text}\n)"]}
            if len(gemini_history) > 1: gemini_history.insert(-1, rag_message)
            else: gemini_history.insert(0, rag_message)
            log.debug("Gemini: Added %d RAG facts.", len(rag_facts))

        # system_instruction = system_prompt_override or self.system_prompt # Больше не нужно здесь

        try:
            # --- ИСПРАВЛЕНИЕ: Убираем system_instruction из вызова ---
            response = await self.model.generate_content_async(
                contents=gemini_history, # Передаем историю и RAG факты
                generation_config=self.generation_config,
                safety_settings=self.DEFAULT_SAFETY_SETTINGS
                # system_instruction=system_instruction # <-- УБРАНО ОТСЮДА
            )
            # ---------------------------------------------------------

            # --- Обработка ответа (оставляем как есть) ---
            if response and response.text:
                log.debug("Gemini response received successfully.")
                return response.text.strip()
            else:
                # ... (обработка пустых/заблокированных ответов) ...
                reason = "Unknown reason"
                try:
                    if response and response.prompt_feedback: reason = f"Blocked by safety settings ({response.prompt_feedback.block_reason})"
                    elif not response: reason = "Empty response object"
                except ValueError: reason = "Unknown or parsing error"
                log.warning("Gemini returned an empty or blocked response. Reason: %s", reason)
                return f"(Я не могу сгенерировать ответ сейчас. Причина: {reason})"
            # --------------------------------------------

        except Exception as e:
            log.exception("Error during Gemini API call in generate(): %s", e)
            return f"(Произошла ошибка при обращении к AI: {type(e).__name__})"

    # --- Метод generate_achievement_name (убираем system_instruction из вызова) ---
    async def generate_achievement_name(
        self,
        context: str,
        style_id: str,
        tone_hint: str,
        style_examples: str
        ) -> List[str]:
        log.debug("Gemini: Generating achievement name...")
        # --- Промпт для названий (оставляем как есть) ---
        system_prompt = "You are a highly creative naming expert..."
        user_prompt = f"""
        ... (Полный текст промпта) ...
        """
        full_prompt_contents = [
             {'role': 'user', 'parts': [system_prompt]},
             {'role': 'model', 'parts': ["Okay, provide the achievement details."]},
             {'role': 'user', 'parts': [user_prompt]}
        ]
        # ---------------------------------------------

        try:
            generation_config_names = GenerationConfig(temperature=0.8, candidate_count=1)
            # --- ИСПРАВЛЕНИЕ: Убираем system_instruction из вызова ---
            response = await self.model.generate_content_async(
                contents=full_prompt_contents,
                generation_config=generation_config_names,
                safety_settings=self.DEFAULT_SAFETY_SETTINGS
            )
            # ------------------------------------------------
            # --- Обработка ответа (оставляем как есть) ---
            if response and response.text:
                # ... (парсинг имен) ...
                lines = [line.strip() for line in response.text.strip().split('\n')]
                names = [ line.split('.', 1)[1].strip() for line in lines if '.' in line and line.split('.', 1)[0].strip().isdigit() ]
                valid_names = names[:3]
                log.info("Gemini generated %d achievement names: %s", len(valid_names), valid_names)
                while len(valid_names) < 3: valid_names.append(f"Default Name {len(valid_names) + 1}")
                return valid_names
            else:
                # ... (обработка пустых/заблокированных ответов) ...
                 reason = "Unknown reason"
                 try:
                     if response and response.prompt_feedback: reason = f"Blocked by safety settings ({response.prompt_feedback.block_reason})"
                 except ValueError: reason = "Unknown or parsing error"
                 log.warning("Gemini returned empty/blocked response for achievement names. Reason: %s", reason)
                 return ["Default Name 1", "Default Name 2", "Default Name 3"]
            # --------------------------------------------
        except Exception as e:
            log.exception("Error during Gemini API call for achievement names: %s", e)
            return ["Default Name 1", "Default Name 2", "Default Name 3"]

    # extract_events остается заглушкой
    async def extract_events(self, text: str) -> List[Event]: return []

__all__ = ["GeminiLLMProvider"]
