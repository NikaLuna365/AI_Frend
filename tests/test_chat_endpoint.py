import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from app.main import app
from app.core.llm.client import LLMClient, Message as LLMMessage, Event
from app.core.calendar.base import get_calendar_provider
from app.core.achievements.service import AchievementsService
from app.db.base import create_db_and_tables, drop_db_and_tables, async_session_context
from app.core.users.models import User
from app.core.auth.security import get_current_user, oauth2_scheme

client = TestClient(app)

@ pytest.fixture(autouse=True)
def patch_dependencies(monkeypatch):
    # Мокаем LLMClient.generate и extract_events
    async def fake_generate(self, prompt, ctx):
        return 'reply text'
    monkeypatch.setattr(LLMClient, 'generate', fake_generate)
    dummy_event = Event(title='Ev', start=__import__('datetime').datetime(2025,1,1,12,0), end=None)
    async def fake_extract(self, txt):
        return [dummy_event]
    monkeypatch.setattr(LLMClient, 'extract_events', fake_extract)
    # Мокаем CalendarProvider
    class FakeCal:
        def add_event(self, user_id, title, start, end=None): pass
        def list_events(self, *args, **kwargs): return []
    monkeypatch.setattr('app.core.calendar.get_calendar_provider', lambda: FakeCal())
    # Мокаем выдачу ачивок
    async def fake_award(self, *a, **kw):
        return []
    monkeypatch.setattr(AchievementsService, 'check_and_award', fake_award)

    async def fake_user():
        async with async_session_context() as session:
            u = await session.get(User, 'u1')
            if not u:
                u = User(id='u1')
                session.add(u)
                await session.commit()
            return u

    app.dependency_overrides[get_current_user] = fake_user
    app.dependency_overrides[oauth2_scheme] = lambda: "token"
    yield
    app.dependency_overrides.clear()

@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    await create_db_and_tables()
    yield
    await drop_db_and_tables()

def test_chat_full_flow():
    payload = {'user_id': 'u1', 'message_text': 'hello'}
    res = client.post('/v1/chat/', json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data['reply_text'] == 'reply text'
    assert isinstance(data['detected_events'], list)
    # Проверяем, что парсинг и вставка события прошли
    assert data['detected_events'][0]['title'] == 'Ev'


def test_first_message_count(monkeypatch):
    recorded: list[int] = []

    async def fake_check(self, uid=None, message_text=None, user_message_count=0, **_):
        recorded.append(user_message_count)
        return []

    monkeypatch.setattr(AchievementsService, 'check_and_award', fake_check)

    client.post('/v1/chat/', json={'user_id': 'u2', 'message_text': 'one'})
    assert recorded[-1] == 1

    client.post('/v1/chat/', json={'user_id': 'u2', 'message_text': 'two'})
    assert recorded[-1] == 2
