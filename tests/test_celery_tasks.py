import pytest
from app.workers.tasks import send_due_reminders, celery_app
from celery import states

@ pytest.fixture(autouse=True)
def celery_eager(monkeypatch):
    celery_app.conf.task_always_eager = True
    yield
    celery_app.conf.task_always_eager = False

def test_send_due_reminders_runs():
    result = send_due_reminders.delay()
    assert result.status in (states.SUCCESS,)
    assert result.result is None
