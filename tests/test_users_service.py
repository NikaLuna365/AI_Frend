import pytest
from app.core.users.service import UsersService
from app.core.llm.client import Message
from app.db.base import Base, engine

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield

def test_save_and_get_messages():
    svc = UsersService()
    svc.save_message('u1', Message(role='user', content='hello'))
    msgs = svc.get_recent_messages('u1')
    assert len(msgs) == 1
    assert msgs[0].content == 'hello'
