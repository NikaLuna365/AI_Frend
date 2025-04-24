import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.llm.client import LLMClient, Message as LLMMessage, Event
from app.core.calendar.base import get_calendar_provider
from app.core.achievements.service import AchievementsService

client = TestClient(app)

@ pytest.fixture(autouse=True)
def patch_dependencies(monkeypatch):
    # Мокаем LLMClient.generate и extract_events
    monkeypatch.setattr(LLMClient, 'generate', lambda self, prompt, ctx: 'reply text')
    dummy_event = Event(title='Ev', start=__import__('datetime').datetime(2025,1,1,12,0))
    monkeypatch.setattr(LLMClient, 'extract_events', lambda self, txt: [dummy_event])
    # Мокаем CalendarProvider
    class FakeCal:
        def add_event(self, user_id, title, start, end=None): pass
        def list_events(self, *args, **kwargs): return []
    monkeypatch.setattr(get_calendar_provider.__module__, 'get_calendar_provider', lambda: FakeCal())
    # Мокаем выдачу ачивок
    monkeypatch.setattr(AchievementsService, 'check_and_award', lambda self, uid, evs, rt: [])
    yield

def test_chat_full_flow():
    payload = {'user_id': 'u1', 'message_text': 'hello'}
    res = client.post('/v1/chat/', json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data['reply_text'] == 'reply text'
    assert isinstance(data['detected_events'], list)
    # Проверяем, что парсинг и вставка события прошли
    assert data['detected_events'][0]['title'] == 'Ev'
