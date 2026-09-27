# Tests run against a real PostgreSQL: start it with
#   docker compose -f compose.yaml -f compose.dev.yaml up -d db

from collections.abc import Iterator

import pytest
from alembic import command
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, make_url, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import get_session
from app.demo import ensure_demo_user
from app.main import app
from app.models import User
from app.prestart import alembic_config

TEST_DATABASE = "podcast_test"


@pytest.fixture(scope="session")
def engine() -> Iterator[Engine]:
    url = make_url(get_settings().database_url.get_secret_value())
    admin = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    try:
        with admin.connect() as connection:
            connection.execute(text(f"DROP DATABASE IF EXISTS {TEST_DATABASE} WITH (FORCE)"))
            connection.execute(text(f"CREATE DATABASE {TEST_DATABASE}"))
    except OperationalError as error:
        raise RuntimeError(
            "PostgreSQL is not reachable. Start it with: "
            "docker compose -f compose.yaml -f compose.dev.yaml up -d db"
        ) from error
    finally:
        admin.dispose()

    test_engine = create_engine(url.set(database=TEST_DATABASE))
    with test_engine.begin() as connection:
        config = alembic_config()
        config.attributes["connection"] = connection
        command.upgrade(config, "head")
    yield test_engine
    test_engine.dispose()


@pytest.fixture
def session(engine: Engine) -> Iterator[Session]:
    with engine.connect() as connection:
        transaction = connection.begin()
        with Session(bind=connection, join_transaction_mode="create_savepoint") as test_session:
            yield test_session
        transaction.rollback()


@pytest.fixture
def demo_user(session: Session) -> User:
    return ensure_demo_user(session)


@pytest.fixture
def test_settings() -> Settings:
    return Settings(
        _env_file=None, openai_api_key=None, elevenlabs_api_key=None, guardian_api_key=None
    )


@pytest.fixture
def client(session: Session, demo_user: User, test_settings: Settings) -> Iterator[TestClient]:
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[get_settings] = lambda: test_settings
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
