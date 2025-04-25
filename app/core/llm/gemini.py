# app/core/llm/gemini.py
import os
import google.generativeai as genai


class GeminiProvider:
    def __init__(self) -> None:
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

    def generate(self, prompt: str, context: list[dict]) -> str:
        model = genai.GenerativeModel("gemini-pro")
        resp = model.generate_content(context + [{"role": "user", "parts": [prompt]}])
        return resp.text
