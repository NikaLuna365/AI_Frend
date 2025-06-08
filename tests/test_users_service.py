# tests/test_users_service.py (Пример)
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

# Предполагается, что эти импорты работают после настройки PYTHONPATH в pytest.ini
from app.core.users.service import UsersService
from app.core.users.models import User, Message as MessageModel
from app.core.llm.message import Message
from app.db.base import async_session_context, create_db_and_tables, drop_db_and_tables

# Фикстура для настройки БД перед тестами модуля/сессии
@pytest_asyncio.fixture(scope="function", autouse=True)  # function scope
async def setup_db():
    # Создаем таблицы перед запуском тестов в модуле
    await create_db_and_tables()
    yield
    # Удаляем таблицы после выполнения всех тестов в модуле
    await drop_db_and_tables()

# Асинхронная фикстура для предоставления сессии
@pytest_asyncio.fixture
async def db_session() -> AsyncSession:
    async with async_session_context() as session:
        yield session

# Помечаем тест как асинхронный
@pytest.mark.asyncio
async def test_ensure_user_creates_new(db_session: AsyncSession):
    """Тест: ensure_user создает нового пользователя."""
    service = UsersService(db_session)
    user_id = "new_user_123"

    # Действие
    user = await service.ensure_user(user_id)
    await db_session.commit() # Коммитим транзакцию явно в тесте

    # Проверка
    assert user is not None
    assert user.id == user_id

    # Проверяем в БД напрямую (убедимся, что коммит сработал)
    async with async_session_context() as verify_session:
        fetched_user = await verify_session.get(User, user_id)
        assert fetched_user is not None
        assert fetched_user.id == user_id

@pytest.mark.asyncio
async def test_ensure_user_finds_existing(db_session: AsyncSession):
    """Тест: ensure_user находит существующего пользователя."""
    service = UsersService(db_session)
    user_id = "existing_user_456"

    # Подготовка: Создаем пользователя заранее
    existing_user = User(id=user_id)
    db_session.add(existing_user)
    await db_session.commit()

    # Действие
    user = await service.ensure_user(user_id)
    # Commit не нужен, так как мы только читали

    # Проверка
    assert user is not None
    assert user.id == user_id
    # Можно проверить, что это тот же объект или имеет те же данные

@pytest.mark.asyncio
async def test_save_message(db_session: AsyncSession):
    """Тест: save_message сохраняет сообщение."""
    service = UsersService(db_session)
    user_id = "user_with_message"
    message_data = Message(role="user", content="Hello Async World!")

    # Действие
    saved_msg_orm = await service.save_message(user_id, message_data)
    await db_session.commit() # Коммитим транзакцию

    # Проверка
    assert saved_msg_orm is not None
    assert saved_msg_orm.user_id == user_id
    assert saved_msg_orm.role == "user"
    assert saved_msg_orm.content == "Hello Async World!"
    assert saved_msg_orm.id is not None # Проверяем, что ID присвоен

    # Проверяем пользователя
    user = await db_session.get(User, user_id)
    assert user is not None

@pytest.mark.asyncio
async def test_get_recent_messages(db_session: AsyncSession):
    """Тест: get_recent_messages возвращает сообщения в правильном порядке."""
    service = UsersService(db_session)
    user_id = "history_user"

    # Подготовка: Создаем пользователя и сообщения
    user = User(id=user_id)
    msg1 = MessageModel(user_id=user_id, role="user", content="First")
    msg2 = MessageModel(user_id=user_id, role="assistant", content="Second")
    msg3 = MessageModel(user_id=user_id, role="user", content="Third")
    db_session.add_all([user, msg1, msg2, msg3])
    await db_session.commit()

    # Действие
    messages = await service.get_recent_messages(user_id, limit=10)

    # Проверка
    assert len(messages) == 3
    assert messages[0]['role'] == "user"
    assert messages[0]['content'] == "First"
    assert messages[1]['role'] == "assistant"
    assert messages[1]['content'] == "Second"
    assert messages[2]['role'] == "user"
    assert messages[2]['content'] == "Third"
