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
    # Mock CalendarProvider
    from app.core.calendar.base import get_calendar_provider
    class FakeProv:
        def all_events(self, user_id):
            event = fake_event.model_dump()
            event["start"] = event["start"].isoformat()
            if event["end"] is not None:
                event["end"] = event["end"].isoformat()
            return [event] if user_id == 'u1' else []
        def add_event(self, *args, **kwargs):
            pass
    import app.api.v1.calendar as calendar_module
    monkeypatch.setattr(calendar_module, 'get_calendar_provider', lambda name=None: FakeProv())
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
