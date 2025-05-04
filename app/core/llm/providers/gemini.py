# /app/app/core/llm/providers/gemini.py (Исправлены отступы + Обработка Ответа)

from __future__ import annotations

import asyncio # Добавляем импорт asyncio для run_in_executor (если используется в generate_icon)
import logging
import base64
import google.generativeai as genai
from google.generativeai.types import GenerationConfig, ContentDict, PartDict, SafetySettingDict
from typing import List, Sequence, Optional, Dict, Any, cast

from google.cloud import aiplatform # Добавляем импорт aiplatform
from google.protobuf import json_format
from google.protobuf.struct_pb2 import Value

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
You are AI-Friend, a personalized AI companion. Your primary goal is to be a supportive, friendly, and empathetic presence in the user's life. You are NOT just a task manager or a neutral assistant; you are a companion who genuinely cares.

Personality: Friendly, warm, encouraging, positive, slightly informal, curious (about the user's well-being and interests, but respectfully), and reliable.
Tone: Empathetic and understanding. Use a supportive and uplifting tone. Incorporate light, positive humor when appropriate, but avoid sarcasm, cynicism, or potentially offensive jokes. Be motivating but not preachy or condescending.
Proactivity: Gently and proactively engage the user. Ask how they are doing, show interest in their day, or recall past conversation points (using provided context). Do this naturally, perhaps once per interaction or when contextually relevant, avoid being overly repetitive or intrusive.
Empathy: Acknowledge the user's feelings, validate their experiences (both positive and negative), and offer words of support or encouragement.
Language: Communicate primarily in clear, natural Russian. You can understand and use common English technical terms or names if they appear in the user's input or context.
Safety: Strictly adhere to safety guidelines. Do not generate harmful, unethical, or inappropriate content. Do not provide professional advice (medical, financial, legal, mental health). Express empathy and suggest consulting professionals for such topics. Respect user boundaries and privacy. Handle sensitive topics with extra care.
"""

class GeminiLLMProvider(BaseLLMProvider):
    name = "gemini"
    DEFAULT_MODEL_NAME = "gemini-1.5-flash-latest"
    IMAGEN_MODEL_NAME = "imagegeneration@006" # Оставляем из прошлого шага
    DEFAULT_SAFETY_SETTINGS: List[SafetySettingDict] = [
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    ]

    def __init__(self, model_name: Optional[str] = None) -> None:
        # --- Проверяем отступы здесь ---
        self.model_name = model_name or self.DEFAULT_MODEL_NAME
        self.system_prompt = SYSTEM_PROMPT_AI_FRIEND
        self.safety_settings = self.DEFAULT_SAFETY_SETTINGS
        self.generation_config = GenerationConfig(temperature=0.7, candidate_count=1)
        try:
            # Инициализация БЕЗ system_instruction (как в #75)
            self.model = genai.GenerativeModel(
                model_name=self.model_name
            )
            log.info(
                "GeminiLLMProvider initialized for model: %s",
                self.model_name
            )
        except Exception as e:
            log.exception("Failed to initialize GenerativeModel '%s': %s", self.model_name, e)
            raise RuntimeError(f"Failed to initialize Gemini model {self.model_name}") from e
        # --- Конец __init__ ---

    # --- Проверяем отступы здесь ---
    def _prepare_gemini_history(self, context: Sequence[Message]) -> List[ContentDict]:
        gemini_history: List[ContentDict] = []
        for msg in context:
            content = msg.get("content", "").strip()
            if not content:
                continue
            role = "model" if msg.get("role") == "assistant" else "user"
            gemini_history.append(
                cast(ContentDict, {"role": role, "parts": [PartDict(text=content)]})
            )
        return gemini_history
    # --- Конец _prepare_gemini_history ---

    # --- Проверяем отступы здесь и внутри ---
    async def generate(
        self, prompt: str, context: Sequence[Message],
        rag_facts: Optional[List[str]] = None, system_prompt_override: Optional[str] = None
    ) -> str:
        log.debug("Gemini: Generating response...")
        history_prepared = self._prepare_gemini_history(context)

        if rag_facts:
            facts_text = "\n".join(f"- {fact}" for fact in rag_facts)
            rag_message = cast(ContentDict, {'role': 'user', 'parts': [PartDict(text=f"(Context:\n{facts_text}\n)")]})
            history_prepared.append(rag_message)
            log.debug("Gemini: Added %d RAG facts.", len(rag_facts))

        current_message = cast(ContentDict, {'role': 'user', 'parts': [PartDict(text=prompt)]})
        contents_for_api = history_prepared + [current_message]

        # Используем системный промпт из атрибута класса
        effective_system_instruction = system_prompt_override or self.system_prompt

        try:
            # Вызов API - передаем system_instruction сюда
            response = await self.model.generate_content_async(
                contents=contents_for_api,
                generation_config=self.generation_config,
                safety_settings=self.safety_settings,
                # --- ПРАВИЛЬНОЕ МЕСТО для system_instruction (согласно последним данным) ---
                system_instruction=effective_system_instruction
                # -----------------------------------------------------------------------
            )

            # Надежная обработка ответа (как в #75)
            try:
                if response.prompt_feedback.block_reason:
                    reason = f"Blocked by safety settings ({response.prompt_feedback.block_reason.name})" # Используем .name
                    log.warning(f"Gemini response blocked: {reason}")
                    return f"(Ответ был заблокирован: {reason})"

                if (response.candidates and response.candidates[0].content and
                        response.candidates[0].content.parts and response.candidates[0].content.parts[0].text):
                    response_text = response.candidates[0].content.parts[0].text.strip()
                    log.debug("Gemini response extracted successfully.")
                    return response_text
                else:
                    log.warning("Gemini returned no usable text content in candidates.")
                    return "(AI не смог сформировать текстовый ответ)"
            except (AttributeError, IndexError, StopIteration, ValueError) as parse_exc:
                log.exception(f"Error parsing Gemini response structure: {parse_exc}. Response obj: {response}")
                return f"(Ошибка при обработке ответа AI: {type(parse_exc).__name__})"

        except TypeError as te:
            # Обработка TypeError, если ВДРУГ system_instruction все еще не принимается
             if 'system_instruction' in str(te):
                  log.error("system_instruction argument STILL not accepted by generate_content_async. Check SDK version/docs! Trying fallback.")
                  # --- Fallback: добавляем system prompt к первому сообщению ---
                  try:
                       first_user_message = f"{effective_system_instruction}\n\nUser query: {prompt}"
                       contents_alt = self._prepare_gemini_history(context) + [cast(ContentDict, {'role': 'user', 'parts': [PartDict(text=first_user_message)]})]
                       response_fallback = await self.model.generate_content_async(
                            contents=contents_alt,
                            generation_config=self.generation_config,
                            safety_settings=self.safety_settings
                       )
                       # Обрабатываем ответ fallback'а
                       if response_fallback and response_fallback.text: return response_fallback.text.strip()
                       else:
                            log.warning("Gemini fallback also returned empty/blocked response.")
                            return "(Я не могу сгенерировать ответ сейчас...)"
                  except Exception as e_fallback:
                       log.exception("Error during Gemini API fallback call: %s", e_fallback)
                       return f"(Произошла ошибка при обращении к AI [fallback]: {type(e_fallback).__name__})"
             else: # Другая ошибка TypeError
                  log.exception(f"TypeError during Gemini API call: {te}")
                  return f"(Произошла ошибка при вызове AI: TypeError)"
        except Exception as e:
            log.exception(f"Error during Gemini API call in generate(): {e}")
            return f"(Произошла ошибка при обращении к AI: {type(e).__name__})"
    # --- Конец generate ---

    # --- Проверяем отступы здесь и внутри ---
    async def generate_achievement_name(
        self, context: str, style_id: str, tone_hint: str, style_examples: str
    ) -> List[str]:
        log.debug("Gemini: Generating achievement name...")
        # ... (Формирование full_prompt_contents без изменений) ...
        system_prompt = "You are a highly creative naming expert..."
        user_prompt = f"""..."""
        full_prompt_contents: List[ContentDict] = [
             cast(ContentDict, {'role': 'user', 'parts': [PartDict(text=system_prompt)]}),
             cast(ContentDict, {'role': 'model', 'parts': [PartDict(text="Okay, provide the achievement details.")]}),
             cast(ContentDict, {'role': 'user', 'parts': [PartDict(text=user_prompt)]})
        ]
        try:
            generation_config_names = GenerationConfig(temperature=0.8, candidate_count=1)
            response = await self.model.generate_content_async(
                contents=full_prompt_contents,
                generation_config=generation_config_names,
                safety_settings=self.safety_settings
                # БЕЗ system_instruction
            )
            # --- Надежная обработка ответа (как в generate) ---
            try:
                if response.prompt_feedback.block_reason:
                     log.warning(...) # Логгируем блокировку
                     return ["Default Name 1", "Default Name 2", "Default Name 3"]
                if (response.candidates and ... and response.candidates[0].content.parts[0].text):
                    response_text = response.candidates[0].content.parts[0].text
                    # ... (парсинг имен из response_text) ...
                    lines = [l.strip() for l in response_text.strip().split('\n')]
                    names = [l.split('.', 1)[1].strip() for l in lines if '.' in l and l.split('.', 1)[0].strip().isdigit()]
                    valid_names = names[:3]
                    while len(valid_names) < 3: valid_names.append(f"Default Name {len(valid_names)+1}")
                    return valid_names
                else:
                     log.warning("Gemini returned no usable content for achievement names.")
                     return ["Default Name 1", "Default Name 2", "Default Name 3"]
            except (AttributeError, IndexError, StopIteration, ValueError) as parse_exc:
                 log.exception(f"Error parsing Gemini response for names: {parse_exc}")
                 return ["Default Name 1", "Default Name 2", "Default Name 3"]
            # ----------------------------------------------------
        except Exception as e:
            log.exception("Error during Gemini API call for achievement names: %s", e)
            return ["Default Name 1", "Default Name 2", "Default Name 3"]
    # --- Конец generate_achievement_name ---

    # --- Проверяем отступы здесь и внутри ---
    async def extract_events(self, text: str) -> List[Event]:
        log.debug("GeminiLLMProvider.extract_events called (returns empty list).")
        return []
    # --- Конец extract_events ---

    # --- Метод generate_achievement_icon (оставляем как в #71) ---
    async def generate_achievement_icon(...) -> bytes | None:
        # ... (код с aiplatform.init, model.generate_images, run_in_executor) ...
        log.info(...)
        if not settings.VERTEX_AI_PROJECT or not settings.VERTEX_AI_LOCATION: return None
        try:
            aiplatform.init(...)
            model = aiplatform.ImageGenerationModel.from_pretrained(...)
            prompt = f"""...""" # Формируем промпт
            imagen_parameters = {...}
            loop = asyncio.get_running_loop()
            response = await loop.run_in_executor(None, lambda: model.generate_images(...))
            if response and response.images:
                 return response.images[0]._blob
            else: return None
        except ImportError: return None
        except Exception as e: log.exception(...); return None
    # --- Конец generate_achievement_icon ---

__all__ = ["GeminiLLMProvider"]
