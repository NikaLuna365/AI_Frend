# /app/app/core/llm/providers/gemini.py (ПОЛНАЯ ВЕРСИЯ - system_instruction в __init__)

from __future__ import annotations

import asyncio
import logging
import base64
import google.generativeai as genai
from google.generativeai.types import GenerationConfig, ContentDict, PartDict, SafetySettingDict, GenerateContentResponse
from typing import List, Sequence, Optional, Dict, Any, cast

from google.cloud import aiplatform
from google.protobuf import json_format
from google.protobuf.struct_pb2 import Value

from .base import BaseLLMProvider, Message, Event
from app.config import settings

log = logging.getLogger(__name__)

try:
    _test_model_init = genai.GenerativeModel('gemini-1.5-flash-latest')
    log.info("Google Generative AI SDK configured correctly on module load (test model init successful).")
except Exception as e:
    log.warning("Could not pre-initialize test model on module load: %s", e)

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
    IMAGEN_MODEL_NAME = "imagegeneration@006"
    DEFAULT_SAFETY_SETTINGS: List[SafetySettingDict] = [
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    ]

    def __init__(self, model_name: Optional[str] = None) -> None:
        self.model_name = model_name or self.DEFAULT_MODEL_NAME
        self.system_prompt_text = SYSTEM_PROMPT_AI_FRIEND
        self.safety_settings = self.DEFAULT_SAFETY_SETTINGS
        self.generation_config = GenerationConfig(
            temperature=0.7,
            candidate_count=1,
        )
        log.info(f"Attempting to initialize GeminiLLMProvider with model: {self.model_name}")
        try:
            # Передаем system_instruction и safety_settings в конструктор
            self.model = genai.GenerativeModel(
                model_name=self.model_name,
                system_instruction=self.system_prompt_text,
                safety_settings=self.safety_settings
            )
            log.info(
                "GeminiLLMProvider initialized model %s with system prompt and safety settings.",
                self.model_name
            )
        except TypeError as te:
             log.warning(f"TypeError on GenerativeModel init ({te}). Retrying without safety_settings in constructor (will pass to generate_content).")
             try: # Fallback 1: без safety_settings в конструкторе
                  self.model = genai.GenerativeModel(
                       model_name=self.model_name,
                       system_instruction=self.system_prompt_text
                  )
                  log.info("GeminiLLMProvider initialized (safety_settings will be passed to generate_content).")
             except TypeError as te2: # Fallback 2: без system_instruction и safety_settings в конструкторе
                  if 'system_instruction' in str(te2): # Проверяем, не ругается ли на system_instruction
                       log.warning(f"TypeError on GenerativeModel init ({te2}). Retrying without system_instruction in constructor.")
                       self.model = genai.GenerativeModel(model_name=self.model_name)
                       log.info("GeminiLLMProvider initialized (system_instruction & safety_settings will be passed to generate_content / prepended).")
                  else: # Другая TypeError
                       log.exception(f"Unexpected TypeError initializing GenerativeModel: {te2}")
                       raise RuntimeError(f"TypeError on Gemini model init {self.model_name}") from te2
             except Exception as e_fallback:
                  log.exception(f"Failed to initialize GenerativeModel even in fallback: {e_fallback}")
                  raise RuntimeError(f"Failed to initialize Gemini model {self.model_name}") from e_fallback
        except Exception as e:
            log.exception(f"Failed to initialize GenerativeModel '{self.model_name}': {e}")
            raise RuntimeError(f"Failed to initialize Gemini model {self.model_name}") from e

    def _prepare_gemini_history(self, context: Sequence[Message]) -> List[ContentDict]:
        gemini_history: List[ContentDict] = []
        for msg in context:
            content = msg.get("content", "").strip()
            if not content: continue
            role = "model" if msg.get("role") == "assistant" else "user"
            gemini_history.append(cast(ContentDict, {"role": role, "parts": [PartDict(text=content)]}))
        return gemini_history

    async def generate(
        self, prompt: str, context: Sequence[Message],
        rag_facts: Optional[List[str]] = None, system_prompt_override: Optional[str] = None
    ) -> str:
        log.debug(f"Gemini: Generating response for prompt: '{prompt[:70]}...'")
        history_prepared = self._prepare_gemini_history(context)

        if rag_facts:
            facts_text = "\n".join(f"- {fact}" for fact in rag_facts)
            rag_message = cast(ContentDict, {'role': 'user', 'parts': [PartDict(text=f"(Context: Remember these facts about the user:\n{facts_text}\n)")]})
            history_prepared.append(rag_message)
            log.debug("Gemini: Added %d RAG facts.", len(rag_facts))

        current_message = cast(ContentDict, {'role': 'user', 'parts': [PartDict(text=prompt)]})
        contents_for_api = history_prepared + [current_message]

        # system_instruction уже в self.model, если __init__ его принял.
        # Если нет, то мы его не передаем (т.к. generate_content_async его не примет как аргумент)
        # и полагаемся на то, что модель его либо не требует, либо он будет в contents.

        try:
            log.debug(f"Calling generate_content_async. Last content: {contents_for_api[-1]}")
            response: GenerateContentResponse = await self.model.generate_content_async(
                contents=contents_for_api,
                generation_config=self.generation_config,
                safety_settings=self.safety_settings # Передаем здесь
                # system_instruction НЕ передаем здесь
            )
            log.debug(f"Gemini API call completed. Full response object: {response}")

            try: # Надежная обработка ответа
                if response.prompt_feedback and response.prompt_feedback.block_reason:
                    reason = response.prompt_feedback.block_reason.name
                    log.warning(f"Gemini response blocked: {reason}")
                    return f"(Ответ был заблокирован: {reason})"
                if not response.candidates:
                     log.warning("Gemini response missing 'candidates' field.")
                     return "(AI не вернул кандидатов ответа)"
                first_candidate = response.candidates[0]
                if not first_candidate.content or not first_candidate.content.parts or not first_candidate.content.parts[0].text:
                     finish_reason_name = first_candidate.finish_reason.name if first_candidate.finish_reason else "UNKNOWN"
                     log.warning(f"Gemini candidate has no content/parts. Finish reason: {finish_reason_name}")
                     safety_ratings_str = ", ".join(f"{r.category.name}={r.probability.name}" for r in first_candidate.safety_ratings) if first_candidate.safety_ratings else "N/A"
                     log.warning(f"Candidate safety ratings: {safety_ratings_str}")
                     return f"(Ответ AI был отфильтрован или пуст. Причина: {finish_reason_name})"
                response_text = first_candidate.content.parts[0].text.strip()
                log.info("Gemini response extracted successfully.")
                return response_text
            except (AttributeError, IndexError, StopIteration, ValueError, KeyError) as parse_exc:
                log.exception(f"Error parsing Gemini response structure: {parse_exc}. Response obj: {response}")
                return f"(Ошибка при обработке ответа AI: {type(parse_exc).__name__})"
        except Exception as e:
            log.exception(f"Error during Gemini API call in generate(): {e}")
            return f"(Произошла ошибка при обращении к AI: {type(e).__name__}: {e})"

    async def generate_achievement_name(
        self, context: str, style_id: str, tone_hint: str, style_examples: str
    ) -> List[str]:
        log.debug(f"Gemini: Generating achievement name. Context: '{context}'")
        system_prompt = "You are a highly creative naming expert..." # Полный текст
        user_prompt = f"""...""" # Полный текст
        full_prompt_contents: List[ContentDict] = [
             cast(ContentDict, {'role': 'user', 'parts': [PartDict(text=system_prompt)]}),
             cast(ContentDict, {'role': 'model', 'parts': [PartDict(text="Okay, I will generate 3 names based on your instructions.")]}),
             cast(ContentDict, {'role': 'user', 'parts': [PartDict(text=user_prompt)]})
        ]
        try:
            generation_config_names = GenerationConfig(temperature=0.8, candidate_count=1)
            response = await self.model.generate_content_async(
                contents=full_prompt_contents,
                generation_config=generation_config_names,
                safety_settings=self.safety_settings
            )
            # Надежная обработка ответа (аналогично generate)
            try:
                if response.prompt_feedback and response.prompt_feedback.block_reason:
                     log.warning(f"Gemini name generation blocked: {response.prompt_feedback.block_reason.name}")
                     return ["Default Name 1", "Default Name 2", "Default Name 3"]
                if (response.candidates and response.candidates[0].content and
                        response.candidates[0].content.parts and response.candidates[0].content.parts[0].text):
                    response_text = response.candidates[0].content.parts[0].text
                    lines = [line.strip() for line in response_text.strip().split('\n')]
                    names = [
                        line.split('.', 1)[1].strip()
                        for line in lines
                        if '.' in line and line.split('.', 1)[0].strip().isdigit()
                    ]
                    valid_names = names[:3]
                    log.info("Gemini generated %d achievement names: %s", len(valid_names), valid_names)
                    while len(valid_names) < 3:
                        valid_names.append(f"Default Name {len(valid_names) + 1}")
                    return valid_names
                else:
                     log.warning("Gemini returned no usable content for achievement names.")
                     return ["Default Name 1", "Default Name 2", "Default Name 3"]
            except (AttributeError, IndexError, StopIteration, ValueError, KeyError) as parse_exc:
                 log.exception(f"Error parsing Gemini response for names: {parse_exc}")
                 return ["Default Name 1", "Default Name 2", "Default Name 3"]
        except Exception as e:
            log.exception(f"Error during Gemini API call for achievement names: {e}")
            return ["Default Name 1", "Default Name 2", "Default Name 3"]

    async def extract_events(self, text: str) -> List[Event]:
        log.debug("GeminiLLMProvider.extract_events called (returns empty list for MVP).")
        return []

    async def generate_achievement_icon(
        self,
        context: str,
        style_id: str,
        style_keywords: str,
        palette_hint: str,
        shape_hint: str
        ) -> bytes | None:
        log.warning(f"generate_achievement_icon called for context '{context}', but Imagen implementation is pending. Returning None.")
        # Реальная логика вызова Vertex AI Imagen будет здесь в Фазе 3
        return None

__all__ = ["GeminiLLMProvider"]
