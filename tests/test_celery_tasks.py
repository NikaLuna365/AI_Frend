import pytest
from app.workers.tasks import generate_achievement_task, celery_app
from celery import states
import asyncio

@ pytest.fixture(autouse=True)
def celery_eager(monkeypatch):
    celery_app.conf.task_always_eager = True
    yield
    celery_app.conf.task_always_eager = False

def test_generate_achievement_task_runs(monkeypatch):
    async def dummy_logic(*args, **kwargs):
        return "OK"

    monkeypatch.setattr(
        "app.workers.tasks._run_generate_achievement_logic", dummy_logic
    )
    result = generate_achievement_task.delay("u1", "code", "theme")
    value = asyncio.get_event_loop().run_until_complete(result.result)
    assert result.status in (states.SUCCESS,)
    assert value == "OK"
