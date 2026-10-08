import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest
from dotenv import dotenv_values
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.models import *  # noqa: F403  (registers models)

ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


@pytest.fixture(scope="session")
def db_engine() -> Iterator[Engine]:
    """Real PostgreSQL, but isolated: tables are created in a throwaway schema that is
    dropped afterwards, so the developer's real `public` tables are never touched.

    Uses the DATABASE_URL from `.env` (the unit-test conftest overrides the env var with a
    dummy, so we read the file directly). Skipped if the database is unreachable.
    """
    url = dotenv_values(ENV_FILE).get("DATABASE_URL")
    if not url:
        pytest.skip("DATABASE_URL not set in .env")
    schema = f"test_{uuid.uuid4().hex[:8]}"
    admin = create_engine(url)
    try:
        with admin.begin() as conn:
            conn.execute(text(f"CREATE SCHEMA {schema}"))
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"PostgreSQL not reachable: {exc.__class__.__name__}")

    engine = create_engine(url, connect_args={"options": f"-csearch_path={schema}"})
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()
    with admin.begin() as conn:
        conn.execute(text(f"DROP SCHEMA {schema} CASCADE"))
    admin.dispose()


@pytest.fixture
def session(db_engine: Engine) -> Iterator[Session]:
    """Each test runs in a transaction that is rolled back, leaving tables empty."""
    connection = db_engine.connect()
    transaction = connection.begin()
    sess = Session(bind=connection, join_transaction_mode="create_savepoint")
    yield sess
    sess.close()
    transaction.rollback()
    connection.close()
