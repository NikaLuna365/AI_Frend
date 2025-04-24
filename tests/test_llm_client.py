import pytest
from app.core.llm.client import LLMClient, Message

class DummyResp:
    last = type('X', (), {'text': 'ok'})

@pytest.fixture(autouse=True)
def patch_genai(monkeypatch):
    import google.generativeai as genai
    class DummyChat:
        @staticmethod
        def create(**kwargs):
            return DummyResp()
    monkeypatch.setattr(genai, 'chat', DummyChat)
    monkeypatch.setattr(genai, 'configure', lambda api_key=None: None)
    yield

def test_generate():
    client = LLMClient()
    res = client.generate('hi', [Message(role='user', content='hello')])
    assert res == 'ok'

def test_extract_events_iso():
    client = LLMClient()
    text = '2025-05-01: Test'
    events = client.extract_events(text)
    assert isinstance(events, list)
