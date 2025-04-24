from fastapi.testclient import TestClient
from app.main import app
from app.core.achievements.models import AchievementRule, Achievement
from app.db.base import SessionLocal, Base, engine
import pytest

client = TestClient(app)

@pytest.fixture(scope='function', autouse=True)
def reset_db():
    # Очистить и пересоздать схему
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    # Добавить правило для теста
    db = SessionLocal()
    rule = AchievementRule(code='first_event', title='First', icon_url='url', description='')
    db.add(rule);
    db.commit()
    yield

def test_achievements_empty():
    res = client.get('/v1/achievements/u1')
    assert res.status_code == 200
    assert res.json() == []

def test_achievements_after_event(monkeypatch):
    # Мокаем extract_events, возвращаем list
    from app.core.llm.client import LLMClient
    monkeypatch.setattr(LLMClient, 'extract_events', lambda self, txt: [None])
    # Отправляем chat, чтобы создать медаль
    res = client.post('/v1/chat/', json={'user_id':'u1','message_text':'hi'})
    assert res.status_code == 200
    ach = client.get('/v1/achievements/u1').json()
    assert any(a['code']=='first_event' for a in ach)
