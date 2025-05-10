# /app/app/core/llm/providers/gemini.py (ПОЛНАЯ ВЕРСИЯ БЕЗ ...)

from __future__ import annotations

import asyncio
import logging
import base64 # Для декодирования ответа Imagen
import google.generativeai as genai
from google.generativeai.types import GenerationConfig, ContentDict, PartDict, SafetySettingDict, GenerateContentResponse
from typing import List, Sequence, Optional, Dict, Any, cast

# Импорты для Vertex AI (Imagen)
from google.cloud import aiplatform
from google.protobuf import json_format
from google.protobuf.struct_pb2 import Value

from .base import BaseLLMProvider, Message, Event
from app.config import settings

log = logging.getLogger(__name__)

# Проверка конфигурации SDK
try:
    _test_model = genai.GenerativeModel('gemini-1.5-flash-latest') # Или ваша целевая модель
    log.info("Google Generative AI SDK seems configured correctly.")
except Exception as e:
    log.warning("Could not pre-initialize test model, potential config issue: %s", e)

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
    DEFAULT_MODEL_NAME = "gemini-1.5-flash-latest" # Можете поменять на "gemini-2.0-flash-lite" если она доступна
    IMAGEN_MODEL_NAME = "imagegeneration@006" # Укажите актуальную версию модели Imagen

    DEFAULT_SAFETY_SETTINGS: List[SafetySettingDict] = [
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    ]

    def __init__(self, model_name: Optional[str] = None) -> None:
        self.model_name = model_name or self.DEFAULT_MODEL_NAME
        self.system_prompt = SYSTEM_PROMPT_AI_FRIEND
        self.safety_settings = self.DEFAULT_SAFETY_SETTINGS
        self.generation_config = GenerationConfig(
            temperature=0.7,
            candidate_count=1,
            # max_output_tokens=2048, # Можно раскомментировать и настроить
        )
        log.info(f"Attempting to initialize GeminiLLMProvider with model: {self.model_name}")
        try:
            # Инициализация БЕЗ system_instruction в конструкторе
            # system_instruction передается в generate_content_async
            self.model = genai.GenerativeModel(model_name=self.model_name)
            log.info(f"GeminiLLMProvider initialized model {self.model_name} successfully.")
        except Exception as e:
            log.exception(f"Failed to initialize GenerativeModel '{self.model_name}': {e}")
            raise RuntimeError(f"Failed to initialize Gemini model {self.model_name}") from e

    def _prepare_gemini_history(self, context: Sequence[Message]) -> List[ContentDict]:
        """Преобразует историю в формат Gemini List[ContentDict]."""
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

    async def generate(
        self, prompt: str, context: Sequence[Message],
        rag_facts: Optional[List[str]] = None, system_prompt_override: Optional[str] = None
    ) -> str:
        log.debug(f"Gemini: Generating response for prompt: '{prompt[:50]}...'")
        history_prepared = self._prepare_gemini_history(context)

        if rag_facts:
            facts_text = "\n".join(f"- {fact}" for fact in rag_facts)
            rag_message = cast(ContentDict, {'role': 'user', 'parts': [PartDict(text=f"(Context: Remember these facts about the user:\n{facts_text}\n)")]})
            history_prepared.append(rag_message) # Добавляем факты перед последним промптом пользователя
            log.debug("Gemini: Added %d RAG facts to history.", len(rag_facts))

        current_message = cast(ContentDict, {'role': 'user', 'parts': [PartDict(text=prompt)]})
        contents_for_api = history_prepared + [current_message]

        effective_system_instruction = system_prompt_override or self.system_prompt

        try:
            log.debug(f"Calling generate_content_async for model '{self.model_name}'. SysPrompt: '{effective_system_instruction[:70]}...'. Last content: {contents_for_api[-1]}")
            response: GenerateContentResponse = await self.model.generate_content_async(
                contents=contents_for_api,
                generation_config=self.generation_config,
                safety_settings=self.safety_settings,
                system_instruction=effective_system_instruction # Передаем system instruction здесь
            )
            log.debug(f"Gemini API call completed. Full response object: {response}")

            try:
                if response.prompt_feedback and response.prompt_feedback.block_reason:
                    reason = response.prompt_feedback.block_reason.name
                    log.warning(f"Gemini response blocked by safety settings: {reason}")
                    return f"(Ответ был заблокирован: {reason})"

                if not response.candidates:
                     log.warning("Gemini response missing 'candidates' field.")
                     return "(AI не вернул кандидатов ответа)"

                first_candidate = response.candidates[0]
                if not first_candidate.content or not first_candidate.content.parts:
                     finish_reason_name = first_candidate.finish_reason.name if first_candidate.finish_reason else "UNKNOWN"
                     log.warning(f"Gemini response candidate has no content/parts. Finish reason: {finish_reason_name}")
                     safety_ratings_str = ", ".join(f"{r.category.name}={r.probability.name}" for r in first_candidate.safety_ratings) if first_candidate.safety_ratings else "N/A"
                     log.warning(f"Candidate safety ratings: {safety_ratings_str}")
                     return f"(Ответ AI был отфильтрован или пуст. Причина: {finish_reason_name})"

                response_text = first_candidate.content.parts[0].text.strip()
                log.info("Gemini response extracted successfully.")
                return response_text
            except (AttributeError, IndexError, StopIteration, ValueError, KeyError) as parse_exc:
                log.exception(f"Error parsing Gemini response structure: {parse_exc}. Full Response Object: {response}")
                return f"(Ошибка при обработке ответа AI: {type(parse_exc).__name__})"

        except Exception as e:
            log.exception(f"Error during Gemini API call in generate(): {e}")
            return f"(Произошла ошибка при обращении к AI: {type(e).__name__}: {e})"


    async def generate_achievement_name(
        self, context: str, style_id: str, tone_hint: str, style_examples: str
    ) -> List[str]:
        log.debug(f"Gemini: Generating achievement name. Context: '{context}'")
        system_prompt = "You are a highly creative naming expert specializing in crafting achievement titles. Your goal is to generate short, catchy, and style-consistent names based on the provided context and style guidance. Adhere strictly to the requested tone and format."
        user_prompt = f"""
Please generate achievement names based on the following details:

*   Achievement Context: "{context}"
*   Target Style Identifier: {style_id}
*   Desired Tone/Keywords: `{tone_hint}`
*   Style Examples (for reference):
{style_examples}

Instructions:
1.  Generate exactly 3 unique achievement name options.
2.  Each name must be short (maximum 4 words).
3.  The names must capture the essence of the "{context}".
4.  Crucially, the names must perfectly match the desired tone described by `{tone_hint}` and feel consistent with the provided `{style_examples}`.
5.  Output *only* a numbered list of the 3 names, with each name on a new line. Do not add any extra text, explanations, or greetings.
"""
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
        log.debug("GeminiLLMProvider.extract_events called (returns empty list).")
        return []

    async def generate_achievement_icon(
        self,
        context: str,
        style_id: str,
        style_keywords: str,
        palette_hint: str,
        shape_hint: str
        ) -> bytes | None:
        """
        Генерирует иконку ачивки (PNG байты) с помощью Vertex AI Imagen API.
        (Реализация пока заглушка, возвращает None)
        """
        log.warning(f"generate_achievement_icon called for context '{context}', but Imagen implementation is pending. Returning None.")
        # --- ЗДЕСЬ БУДЕТ РЕАЛЬНЫЙ КОД ВЫЗОВА VERTEX AI IMAGEN ---
        # try:
        #     aiplatform.init(project=settings.VERTEX_AI_PROJECT, location=settings.VERTEX_AI_LOCATION)
        #     model = aiplatform.ImageGenerationModel.from_pretrained(self.IMAGEN_MODEL_NAME)
        #     prompt_for_imagen = f"A minimalist achievement badge icon: '{context}'. Style: {style_keywords}, colors: {palette_hint}, shape: {shape_hint}. Flat design, no text."
        #     log.debug(f"Imagen prompt: {prompt_for_imagen}")
        #     imagen_parameters = {"number_of_images": 1} # Упрощенные параметры
        #
        #     loop = asyncio.get_running_loop()
        #     response_imagen = await loop.run_in_executor(
        #         None,
        #         lambda: model.generate_images(prompt=prompt_for_imagen, **imagen_parameters)
        #     )
        #
        #     if response_imagen and response_imagen.images:
        #         # API Imagen возвращает изображения в base64, если не указан GCS URI
        #         # или байты напрямую в зависимости от версии SDK.
        #         # Проверяем, есть ли _blob (для байтов) или base64_image_bytes
        #         if hasattr(response_imagen.images[0], '_blob') and response_imagen.images[0]._blob:
        #             png_bytes = response_imagen.images[0]._blob
        #         elif hasattr(response_imagen.images[0], 'base64_image_bytes') and response_imagen.images[0].base64_image_bytes:
        #             png_bytes = base64.b64decode(response_imagen.images[0].base64_image_bytes)
        #         else:
        #             log.warning("Imagen response did not contain image bytes in expected format.")
        #             return None
        #         log.info(f"Imagen generated icon successfully ({len(png_bytes)} bytes).")
        #         return png_bytes
        #     else:
        #         log.warning("Imagen API returned no images or an unexpected response.")
        #         return None
        #
        # except ImportError:
        #      log.error("google-cloud-aiplatform library not found. Cannot generate icons.")
        #      return None
        # except Exception as e:
        #     log.exception(f"Error during Imagen API call: {e}")
        #     return None
        # --- КОНЕЦ РЕАЛЬНОГО КОДА ---
        return None # Возвращаем None, пока не реализовано

__all__ = ["GeminiLLMProvider"]
