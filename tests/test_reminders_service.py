import os
import sys
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta

# Ensure environment and path setup like other tests
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ.setdefault("JWT_SECRET_KEY", "test-secret")
import app.conftest  # noqa: F401

from app.core.reminders.service import RemindersService
from app.db.base import async_session_context, create_db_and_tables, drop_db_and_tables


@pytest_asyncio.fixture(scope="function", autouse=True)
async def setup_db():
    await create_db_and_tables()
    yield
    await drop_db_and_tables()


@pytest_asyncio.fixture
async def db_session() -> AsyncSession:
    async with async_session_context() as session:
        yield session


@pytest.mark.asyncio
async def test_create_and_list_due(db_session: AsyncSession):
    service = RemindersService(db_session)
    due_time = datetime.utcnow() - timedelta(minutes=1)

    reminder = await service.create_reminder("u1", "test", due_time)
    await db_session.commit()

    due = await service.list_due_and_unsent()
    assert any(r.id == reminder.id for r in due)


@pytest.mark.asyncio
async def test_mark_sent_excludes_from_due_list(db_session: AsyncSession):
    service = RemindersService(db_session)
    due_time = datetime.utcnow() - timedelta(minutes=1)

    reminder = await service.create_reminder("u1", "test", due_time)
    await db_session.commit()

    await service.mark_sent(reminder.id)
    await db_session.commit()

    due_after = await service.list_due_and_unsent()
    assert all(r.id != reminder.id for r in due_after)

    updated = await service.get_reminder_by_id(reminder.id)
    assert updated.sent is True


@pytest.mark.asyncio
async def test_delete_reminder(db_session: AsyncSession):
    service = RemindersService(db_session)
    due_time = datetime.utcnow() + timedelta(minutes=5)
    reminder = await service.create_reminder("u2", "del", due_time)
    await db_session.commit()

    removed = await service.delete_reminder(reminder.id)
    await db_session.commit()
    assert removed is True

    fetched = await service.get_reminder_by_id(reminder.id)
    assert fetched is None
