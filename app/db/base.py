from __future__ import annotations

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, scoped_session

from app.config import settings

engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True, future=True)
SessionLocal = scoped_session(sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True))
Base = declarative_base()


@contextmanager
def get_db_session() -> Generator:
    """Dependency для FastAPI и тестов."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:  # pragma: no cover
        db.rollback()
        raise
    finally:
        db.close()
