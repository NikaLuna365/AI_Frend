# /app/app/core/llm/providers/gemini.py (Исправлена обработка ответа)

# ... (импорты, SYSTEM_PROMPT_AI_FRIEND, __init__, _prepare_gemini_history - без изменений по сравнению с v5) ...
from google.generativeai.types import GenerateContentResponse # Импортируем тип ответа

class GeminiLLMProvider(BaseLLMProvider):
    # ... (name, DEFAULT_MODEL_NAME, DEFAULT_SAFETY_SETTINGS, __init__, _prepare_gemini_history) ...

    async def generate(
        self, prompt: str, context: Sequence[Message],
        rag_facts: Optional[List[str]] = None, system_prompt_override: Optional[str] = None
    ) -> str:
        log.debug("Gemini: Generating response...")
        # ... (код подготовки contents_for_api и system_instruction без изменений) ...
        history_prepared = self._prepare_gemini_history(context)
        if rag_facts: # ... (добавление RAG) ...
            facts_text = "\n".join(f"- {fact}" for fact in rag_facts); rag_message = cast(ContentDict, {'role': 'user', 'parts': [PartDict(text=f"(Context:\n{facts_text}\n)")]}); history_prepared.append(rag_message)
        current_message = cast(ContentDict, {'role': 'user', 'parts': [PartDict(text=prompt)]})
        contents_for_api = history_prepared + [current_message]
        effective_system_instruction = system_prompt_override or self.system_prompt

        try:
            # Вызов API (без изменений, system_instruction в конструкторе модели)
            response: GenerateContentResponse = await self.model.generate_content_async(
                contents=contents_for_api,
                generation_config=self.generation_config,
                safety_settings=self.safety_settings
            )

            # --- ИСПРАВЛЕНИЕ: Надежная обработка ответа ---
            try:
                # 1. Проверяем блокировку из-за безопасности
                if response.prompt_feedback.block_reason:
                    reason = response.prompt_feedback.block_reason.name # Получаем имя причины
                    log.warning(f"Gemini response blocked by safety settings: {reason}")
                    return f"(Ответ был заблокирован: {reason})"

                # 2. Пытаемся извлечь текст из первого кандидата
                # Добавляем проверки на всех уровнях вложенности
                if response.candidates \
                   and response.candidates[0].content \
                   and response.candidates[0].content.parts:
                    response_text = response.candidates[0].content.parts[0].text
                    if response_text: # Убедимся, что текст не пустой
                        log.debug("Gemini raw response text extracted successfully.")
                        return response_text.strip()
                    else:
                        log.warning("Gemini returned content part with empty text.")
                        return "(AI вернул пустой ответ)"
                else:
                    log.warning("Gemini returned no usable candidates or content parts.")
                    return "(AI не смог сгенерировать контент)"

            except (AttributeError, IndexError, StopIteration, ValueError) as e_parse:
                # Ловим ошибки, если структура ответа неожиданная
                log.exception(f"Error parsing Gemini response structure: {e_parse}. Response object: {response}")
                return "(Ошибка при обработке ответа AI)"
            # -------------------------------------------------

        except Exception as e:
            log.exception(f"Error during Gemini API call in generate(): {e}")
            return f"(Произошла ошибка при обращении к AI: {type(e).__name__})"

    # --- Метод generate_achievement_name (применяем ту же логику обработки ответа) ---
    async def generate_achievement_name(...) -> List[str]:
        # ... (формирование промпта) ...
        try:
            response = await self.model.generate_content_async(...)

            # --- ИСПРАВЛЕНИЕ: Надежная обработка ответа ---
            try:
                if response.prompt_feedback.block_reason:
                    log.warning(...)
                    return ["Default Name 1 (Blocked)", "Default Name 2", "Default Name 3"]

                if response.candidates and ...: # Проверки как в generate
                    response_text = response.candidates[0].content.parts[0].text
                    if response_text:
                        # ... (парсинг имен из response_text) ...
                        return valid_names
                    else: # ...
                        return ["Default Name 1 (Empty Text)", "Default Name 2", "Default Name 3"]
                else: # ...
                    return ["Default Name 1 (No Content)", "Default Name 2", "Default Name 3"]
            except (AttributeError, IndexError, StopIteration, ValueError) as e_parse:
                 log.exception(...)
                 return ["Default Name 1 (Parse Error)", "Default Name 2", "Default Name 3"]
            # -------------------------------------------------
        except Exception as e:
            log.exception(...)
            return ["Default Name 1 (API Error)", "Default Name 2", "Default Name 3"]


    async def extract_events(self, text: str) -> List[Event]: return []

__all__ = ["GeminiLLMProvider"]
