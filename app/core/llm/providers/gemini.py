# app/core/llm/providers/gemini.py
"""
Google Gemini provider (placeholder).

В CI он не инициализируется – импортируется только если
`settings.LLM_PROVIDER == 'gemini'` в prod/dev; поэтому здесь
достаточно бросить понятное исключение, чтобы тесты не ломались.
"""

from __future__ import annotations

from typing import List

from .base import BaseLLMProvider, Event, Message


class GeminiLLMProvider(BaseLLMProvider):  # pragma: no cover – not used in CI
    name = "gemini"

    def __init__(self) -> None:
        try:
            import google.generativeai  # noqa: F401
        except ModuleNotFoundError as exc:  # pragma: no cover
            raise RuntimeError(
                "Google Gemini SDK not installed. "
                "Add `google-generativeai` to requirements for prod usage."
            ) from exc

        # real initialisation omitted for brevity

    # ------------------------------------------------------------------ #
    def generate(self, prompt: str, context: List[Message] | None = None) -> str:
        raise NotImplementedError("Gemini integration not implemented in OSS build")

    def extract_events(self, text: str) -> List[Event]:
        raise NotImplementedError


__all__: list[str] = ["GeminiLLMProvider"]
