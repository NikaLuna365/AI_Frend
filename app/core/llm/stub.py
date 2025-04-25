# app/core/llm/stub.py
class StubProvider:
    def generate(self, prompt: str, context: list[dict]) -> str:
        return f"[stub‐reply to: {prompt}]"
