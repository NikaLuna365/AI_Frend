# /app/app/core/llm/providers/gemini.py (Исправленная Обработка Ответа)

# ... (импорты, определение класса, __init__, _prepare_gemini_history - без изменений) ...

    async def generate(
        self, prompt: str, context: Sequence[Message],
        rag_facts: Optional[List[str]] = None, system_prompt_override: Optional[str] = None
    ) -> str:
        log.debug("Gemini: Generating response...")
        # ... (подготовка contents_for_api и system_instruction без изменений) ...
        contents_for_api = [...] # Как в ответе #73
        effective_system_instruction = system_prompt_override or self.system_prompt

        try:
            # Вызов API (system_instruction в __init__, остальное здесь)
            response = await self.model.generate_content_async(
                contents=contents_for_api,
                generation_config=self.generation_config,
                safety_settings=self.safety_settings,
                # system_instruction=effective_system_instruction, # Передаем в __init__
            )

            # --- ИСПРАВЛЕНИЕ: НАДЕЖНАЯ ОБРАБОТКА ОТВЕТА ---
            try:
                # 1. Проверяем блокировку safety settings
                if response.prompt_feedback.block_reason:
                    reason = f"Blocked by safety settings ({response.prompt_feedback.block_reason})"
                    log.warning(f"Gemini response blocked: {reason}")
                    return f"(Ответ был заблокирован: {response.prompt_feedback.block_reason.name})" # Используем имя причины

                # 2. Пытаемся извлечь текст из первого кандидата
                # Добавляем проверки на каждом уровне
                if (response.candidates
                        and response.candidates[0].content
                        and response.candidates[0].content.parts
                        and response.candidates[0].content.parts[0].text):

                    response_text = response.candidates[0].content.parts[0].text.strip()
                    log.debug("Gemini response extracted successfully.")
                    return response_text
                else:
                    # Если структура ответа неполная, но не было блокировки
                    log.warning("Gemini returned no usable text content in candidates.")
                    return "(AI не смог сформировать текстовый ответ)"

            except (AttributeError, IndexError, StopIteration, ValueError) as parse_exc:
                # Ловим ошибки доступа к атрибутам или парсинга структуры
                log.exception(f"Error parsing Gemini response structure: {parse_exc}. Response: {response}")
                return f"(Ошибка при обработке ответа AI: {type(parse_exc).__name__})"
            # ----------------------------------------------------

        except Exception as e:
            log.exception(f"Error during Gemini API call in generate(): {e}")
            return f"(Произошла ошибка при обращении к AI: {type(e).__name__})"


    # --- Метод generate_achievement_name (также исправляем обработку ответа) ---
    async def generate_achievement_name(...) -> List[str]:
        # ... (формирование промпта) ...
        full_prompt_contents = [...]
        try:
            generation_config_names = GenerationConfig(...)
            response = await self.model.generate_content_async(
                 contents=full_prompt_contents,
                 generation_config=generation_config_names,
                 safety_settings=self.safety_settings
            )
            # --- ИСПРАВЛЕНИЕ: НАДЕЖНАЯ ОБРАБОТКА ОТВЕТА ---
            try:
                if response.prompt_feedback.block_reason:
                     log.warning(...)
                     return ["Default Name 1", "Default Name 2", "Default Name 3"]

                if (response.candidates and ... and response.candidates[0].content.parts[0].text):
                    response_text = response.candidates[0].content.parts[0].text
                    # ... (парсинг имен из response_text) ...
                    return valid_names
                else:
                     log.warning("Gemini returned no usable content for achievement names.")
                     return ["Default Name 1", "Default Name 2", "Default Name 3"]
            except (AttributeError, IndexError, StopIteration, ValueError) as parse_exc:
                 log.exception(f"Error parsing Gemini response for names: {parse_exc}")
                 return ["Default Name 1", "Default Name 2", "Default Name 3"]
            # ----------------------------------------------------
        except Exception as e:
            log.exception(...)
            return ["Default Name 1", "Default Name 2", "Default Name 3"]

    # ... (extract_events, generate_achievement_icon) ...

__all__ = ["GeminiLLMProvider"]
