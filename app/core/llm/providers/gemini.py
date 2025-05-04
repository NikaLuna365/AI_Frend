# /app/app/core/llm/providers/gemini.py (Финальная версия v4)

from __future__ import annotations

import logging
import google.generativeai as genai
from google.generativeai.types import GenerationConfig # Убрали SafetySetting/HarmCategory
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
        # Сохраняем системный промпт как атрибут для передачи в конструктор
        self.system_prompt = SYSTEM_PROMPT_AI_FRIEND
        # Сохраняем настройки безопасности
        self.safety_settings = self.DEFAULT_SAFETY_SETTINGS
         # Сохраняем конфиг генерации
        self.generation_config = GenerationConfig(
            temperature=0.7,
            candidate_count=1,
        )
        try:
            # --- ИСПРАВЛЕНИЕ: Передаем system_instruction в конструктор ---
            # --- Также передаем safety_settings и generation_config сюда, ---
            # --- если конструктор их принимает (проверяем по факту или докам) ---
            self.model = genai.GenerativeModel(
                model_name=self.model_name,
                system_instruction=self.system_prompt,
                safety_settings=self.safety_settings,
                # generation_config=self.generation_config # generation_config обычно передается в generate_content
            )
            # -------------------------------------------------------------
            log.info(
                "GeminiLLMProvider initialized for model: %s with system prompt and safety settings.",
                self.model_name
            )
        except TypeError as te:
             # Если конструктор НЕ ПРИНИМАЕТ safety_settings или generation_config
             log.warning("Got TypeError on GenerativeModel init (maybe safety/generation config moved to generate_content?): %s", te)
             log.info("Retrying GenerativeModel init without safety/generation config...")
             try:
                  self.model = genai.GenerativeModel(
                       model_name=self.model_name,
                       system_instruction=self.system_prompt
                  )
                  log.info("GeminiLLMProvider initialized successfully (safety/generation config will be passed to generate_content).")
             except Exception as e_fallback:
                  log.exception("Failed to initialize GenerativeModel even in fallback: %s", e_fallback)
                  raise RuntimeError(f"Failed to initialize Gemini model {self.model_name}") from e_fallback
        except Exception as e:
            log.exception("Failed to initialize GenerativeModel '%s': %s", self.model_name, e)
            raise RuntimeError(f"Failed to initialize Gemini model {self.model_name}") from e

    # --- Вспомогательная функция _prepare_gemini_history ---
    def _prepare_gemini_history(self, context: Sequence[Message], current_prompt: Optional[str] = None) -> List[Dict[str, Any]]:
        gemini_history = []
        for msg in context:
            content = msg.get("content", "").strip();
            if not content: continue
            role = "model" if msg.get("role") == "assistant" else "user"
            gemini_history.append({'role': role, 'parts': [content]})
        # НЕ добавляем current_prompt здесь, т.к. generate_content_async принимает contents=history
        # и prompt передается как последний элемент history (если используем generate_content)
        # ИЛИ если используем chat_session, то prompt передается в send_message.
        # Оставим пока добавление prompt в generate().
        return gemini_history

    # --- Метод generate ---
    async def generate(
        self, prompt: str, context: Sequence[Message],
        rag_facts: Optional[List[str]] = None, system_prompt_override: Optional[str] = None # override не будет работать
        ) -> str:
        log.debug("Gemini: Generating response...")
        # Готовим историю (без последнего prompt'а, т.к. он идет в send_message)
        gemini_history_prepared = self._prepare_gemini_history(context, None)

        # Добавляем RAG факты в ИСТОРИЮ перед последним сообщением
        if rag_facts:
            facts_text = "\n".join(f"- {fact}" for fact in rag_facts)
            rag_message = {'role': 'user', 'parts': [f"(Context: Remember these facts about the user:\n{facts_text}\n)"]}
            gemini_history_prepared.append(rag_message)
            log.debug("Gemini: Added %d RAG facts.", len(rag_facts))

        # Если используется system_prompt_override, нужно было бы пересоздать модель,
        # но пока игнорируем эту опцию для простоты.

        try:
            # --- Используем Chat Session (предпочтительно для диалогов) ---
            # Начинаем чат с подготовленной историей
            chat_session = self.model.start_chat(history=gemini_history_prepared)
            # Отправляем последнее сообщение пользователя
            # Передаем safety_settings и generation_config здесь, если их не приняли в __init__
            response = await chat_session.send_message_async(
                 content=prompt, # Передаем только текущее сообщение
                 generation_config=self.generation_config,
                 safety_settings=self.safety_settings
            )
            # --------------------------------------------------------------

            # --- Обработка ответа ---
            if response and response.text:
                log.debug("Gemini response received successfully.")
                return response.text.strip()
            else:
                reason = "Unknown reason"; # ... (код определения reason) ...
                log.warning("Gemini returned empty/blocked response. Reason: %s", reason)
                return f"(Я не могу сгенерировать ответ сейчас. Причина: {reason})"

        except Exception as e:
            log.exception("Error during Gemini API call in generate(): %s", e)
            return f"(Произошла ошибка при обращении к AI: {type(e).__name__})"

    # --- Метод generate_achievement_name (без system_instruction) ---
    async def generate_achievement_name(
        self, context: str, style_id: str, tone_hint: str, style_examples: str
    ) -> List[str]:
        log.debug("Gemini: Generating achievement name...")
        # --- Формируем промпт (оставляем как есть) ---
        system_prompt = "You are a highly creative naming expert..."
        user_prompt = f"""..."""
        full_prompt_contents = [ {'role': 'user', 'parts': [system_prompt]}, ...]
        # ---------------------------------------------
        try:
            generation_config_names = GenerationConfig(temperature=0.8, candidate_count=1)
            # --- Вызов без system_instruction ---
            response = await self.model.generate_content_async(
                contents=full_prompt_contents,
                generation_config=generation_config_names,
                safety_settings=self.safety_settings
            )
            # ---------------------------------
            # --- Обработка ответа (оставляем как есть) ---
            if response and response.text: # ... (парсинг имен) ...
                return valid_names
            else: # ... (обработка пустых/заблокированных) ...
                return ["Default Name 1", "Default Name 2", "Default Name 3"]
        except Exception as e: # ... (обработка ошибок) ...
            return ["Default Name 1", "Default Name 2", "Default Name 3"]

    async def extract_events(self, text: str) -> List[Event]: return []

__all__ = ["GeminiLLMProvider"]
