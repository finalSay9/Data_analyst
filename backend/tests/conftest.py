"""
Shared pytest fixtures.

We test the ingestion service against in-memory SQLite rather than a real
Postgres instance. This works because dataset_service.py builds DDL using
SQLAlchemy's dialect-agnostic type objects (Integer, Float, etc. -- see
type_inference.sqlalchemy_type_for) instead of raw Postgres type strings.
SQLite is a stand-in for testing structure/logic; Postgres is still the
real target in dev/prod (see docker-compose.yml).
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base


@pytest.fixture
def engine():
    # StaticPool + check_same_thread=False: FastAPI's TestClient runs the
    # app in a separate thread from the test itself. SQLite's :memory:
    # database is normally thread-isolated (each new connection gets its
    # own empty DB), so without this, the app thread and test thread
    # would see two different, disconnected databases. StaticPool forces
    # every connection through the same single underlying connection.
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(eng)  # creates the fixed schema: datasets, dataset_columns
    yield eng
    eng.dispose()


@pytest.fixture
def db_session(engine):
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()
