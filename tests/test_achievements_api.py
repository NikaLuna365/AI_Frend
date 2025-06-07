import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.main import app
from app.db.base import create_db_and_tables, drop_db_and_tables, async_session_context
from app.core.users.models import User
from app.core.achievements.models import Achievement
from app.core.auth.security import get_current_user, oauth2_scheme

client = TestClient(app)

@pytest.fixture(scope="function", autouse=True)
async def setup_db():
    await create_db_and_tables()
    async with async_session_context() as session:
        session.add(User(id="u1"))
    yield
    await drop_db_and_tables()

@pytest.fixture(autouse=True)
def override_auth():
    async def fake_user():
        async with async_session_context() as session:
            return await session.get(User, "u1")
    app.dependency_overrides[get_current_user] = fake_user
    app.dependency_overrides[oauth2_scheme] = lambda: "token"
    yield
    app.dependency_overrides.clear()

def test_achievements_empty():
    res = client.get("/v1/achievements/me")
    assert res.status_code == 200
    assert res.json() == []

@pytest.mark.asyncio
async def test_achievements_after_message(monkeypatch):
    from app.core.llm.client import LLMClient
    monkeypatch.setattr(LLMClient, "extract_events", lambda self, txt: [None])
    monkeypatch.setattr(LLMClient, "generate", lambda self, prompt, ctx: "ok")

    chat_res = client.post("/v1/chat/", json={"message_text": "hi"})
    assert chat_res.status_code == 200

    # achievements are created in PENDING state, so /me still returns empty
    res = client.get("/v1/achievements/me")
    assert res.status_code == 200
    assert res.json() == []

    # verify pending achievement exists in DB
    async with async_session_context() as session:
        achs = (await session.execute(select(Achievement))).scalars().all()
        assert any(a.code == "first_message_sent" for a in achs)
