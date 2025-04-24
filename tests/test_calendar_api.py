from fastapi.testclient import TestClient
from app.main import app
from app.core.calendar.models import EventOut
from datetime import datetime, timedelta
import pytest

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_user_and_events(tmp_path, monkeypatch):
    # Создадим фейковый event для пользователя 'u1'
    fake_event = EventOut(
        title="Test Event",
        start=datetime.utcnow() + timedelta(days=1),
        end=None
    )
    # Мокаем CalendarProvider.list_events
    from app.core.calendar.base import get_calendar_provider
    class FakeProv:
        def list_events(self, user_id, from_dt, to_dt):
            return [fake_event] if user_id == 'u1' else []
        def add_event(self, *args, **kwargs):
            pass
    monkeypatch.setattr(get_calendar_provider.__module__, 'get_calendar_provider', lambda: FakeProv())
    yield

def test_get_calendar_returns_events():
    response = client.get('/v1/calendar/u1')
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert data[0]['title'] == 'Test Event'

def test_get_calendar_empty():
    response = client.get('/v1/calendar/other')
    assert response.status_code == 200
    assert response.json() == []
