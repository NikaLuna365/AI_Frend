from app.core.reminders.service import RemindersService
import pytest

@pytest.fixture(scope='function')
def svc_and_cleanup():
    svc = RemindersService()
    # чистим таблицу
    svc.db.query(svc.db.get_bind().table_names()).delete()
    svc.db.commit()
    yield svc

def test_reminders_record_and_exists(svc_and_cleanup):
    svc = svc_and_cleanup
    user, evt = 'u1','e1'
    assert not svc.exists(user, evt)
    svc.record(user, evt)
    assert svc.exists(user, evt)
