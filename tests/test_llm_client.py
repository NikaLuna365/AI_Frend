import pytest
from app.core.llm.client import LLMClient, Message
from app.core.llm.providers.stub import StubLLMProvider

@pytest.fixture(autouse=True)
def use_stub_provider(monkeypatch):
    """Force LLMClient to use the async stub provider."""
    monkeypatch.setenv("LLM_PROVIDER", "stub")
    # reset cached provider instance if it was already created
    import app.core.llm.providers as providers
    providers._provider_instance = None
    yield

@pytest.mark.asyncio
async def test_generate():
    client = LLMClient()
    res = await client.generate('hi', [Message(role='user', content='hello')])
    assert res == 'ok'

@pytest.mark.asyncio
async def test_extract_events_iso():
    client = LLMClient()
    text = '2025-05-01: Test'
    events = await client.extract_events(text)
    assert isinstance(events, list)
