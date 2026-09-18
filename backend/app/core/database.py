"""
Database setup: engine, session factory, declarative base.

Design notes:
- We use SQLAlchemy Core + ORM together deliberately: the ORM manages our
  *fixed* schema (Dataset, DatasetColumn metadata tables), while raw Core
  (engine.connect() + text()/Table reflection) will manage the *dynamic*
  per-upload tables in Phase 1's ingestion service. Alembic only tracks
  the fixed schema — dynamic tables are intentionally outside its scope.
- `get_db()` is a generator dependency: FastAPI calls it per-request,
  guarantees the session is closed even if the endpoint raises.
"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings

engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""

    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
