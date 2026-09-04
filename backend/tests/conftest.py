"""
Shared pytest fixtures for unit and integration tests.

IMPORTANT — import order:
Environment variables must be set before anything imports the
`app` package, because `app.core.config` reads them once, at module import
time (see `getenv()` in app/core/config.py). Therefore, this file sets
env vars right at the top, before any `from app... import`.

Integration tests require a real Postgres (see docker-compose.yml
in the repo root). They connect to a separate `swarm_db_test` database on
`localhost` so as not to overwrite anything in the development database — and
**always** force this URL, overwriting `DATABASE_URL`, even if you have
exported another `DATABASE_URL` (e.g., from `.env` pointing to the `postgres`
host, which exists only in the docker-compose network and is unreachable from
your machine). Tests themselves shouldn't depend on what you currently have
set in the shell for development/docker mode — hence the conscious override,
not `setdefault`.

If you want to test on a different database/host, set `TEST_DATABASE_URL`
(not `DATABASE_URL`) — this is the only variable it honors.

If the `swarm_db_test` database does not exist, the `db_engine` fixture creates
it automatically (requires the POSTGRES_USER to have CREATEDB privilege —
the default user from docker-compose has it).

Running:
    docker compose up -d postgres          # from the repo root
    cd backend
    uv run pytest                          # everything (requires Postgres)
    uv run pytest -m "not integration"     # only fast unit tests
"""

import os

# Conscious override (not setdefault!) — see explanation above. Tests
# must be hermetic regarding what is set in the shell/`.env`
# for development or docker mode.
os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://aiswarm:test1234@localhost:5432/swarm_db_test",
)
os.environ["REDIS_URL"] = "redis://localhost:6379/1"
os.environ["LLM_STUB"] = "1"
os.environ.setdefault("HITL_ACTOR", "test-operator")
os.environ["OLLAMA_BASE_URL"] = "http://localhost:11434-test-unused"
os.environ["OLLAMA_MODEL"] = "test-model-unused"

import uuid  # noqa: E402
from collections.abc import Generator  # noqa: E402

import psycopg  # noqa: E402
import pytest  # noqa: E402
from app.core.config import DATABASE_URL  # noqa: E402
from app.core.db import Base, SessionLocal, engine, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models.affiliate_program import AffiliateProgram  # noqa: E402
from app.models.content_item import ContentItem  # noqa: E402
from app.models.hitl_decision import HitlDecision  # noqa: E402
from app.models.task import AgentTask  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import event  # noqa: E402
from sqlalchemy.engine import Engine  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402


def _ensure_database_exists(database_url: str) -> None:
    """Creates the test database if it does not already exist.

    Connects to the "postgres" database (maintenance db) with the same user
    and password as the rest of the application, just to execute
    `CREATE DATABASE`. Ignores the error if the database already exists.
    """
    # postgresql+psycopg://user:pass@host:port/dbname -> split into parts
    without_scheme = database_url.split("://", 1)[1]
    creds_host, dbname = without_scheme.rsplit("/", 1)
    admin_dsn = f"postgresql://{creds_host}/postgres"

    with psycopg.connect(admin_dsn, autocommit=True) as conn:
        exists = conn.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s", (dbname,)
        ).fetchone()
        if not exists:
            try:
                conn.execute(f'CREATE DATABASE "{dbname}"')
            except psycopg.errors.DuplicateDatabase:
                # someone else (e.g., a parallel test process) managed to
                # create the database between our SELECT and CREATE
                pass


@pytest.fixture(scope="session")
def db_engine() -> Generator[Engine]:
    """Engine connected to the test database, with the schema created."""
    _ensure_database_exists(DATABASE_URL)
    Base.metadata.create_all(bind=engine)
    yield engine


@pytest.fixture()
def db_session(db_engine: Engine) -> Generator[Session]:
    """Session isolated by a transaction, rolled back after each test.

    Application code (endpoints) calls `db.commit()` inside requests.
    So that this doesn't "leak" between tests, the session is bound to an
    external transaction + a SAVEPOINT, which is restored after each commit.
    This is the official technique from the SQLAlchemy documentation for
    testing ("joining a session into an external transaction").
    """
    connection = db_engine.connect()
    outer_transaction = connection.begin()
    session = Session(bind=connection)

    nested = connection.begin_nested()

    @event.listens_for(session, "after_transaction_end")
    def _restart_savepoint(sess: Session, transaction: object) -> None:
        nonlocal nested
        if not nested.is_active:
            nested = connection.begin_nested()

    try:
        yield session
    finally:
        session.close()
        outer_transaction.rollback()
        connection.close()


@pytest.fixture()
def client(db_session: Session) -> Generator[TestClient]:
    """Client with get_db dependency overridden by a transactional session."""

    def _override_get_db() -> Generator[Session]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.fixture()
def make_program(db_session: Session):
    """Factory for quickly creating AffiliateProgram in tests."""

    def _make(**overrides: object) -> AffiliateProgram:
        defaults = {
            "name": f"Test Program {uuid.uuid4().hex[:8]}",
            "url": "https://example.com/aff",
            "network": "TestNetwork",
            "category": "SaaS",
            "rationale": "High EPC and high commission.",
            "status": "proposed",
        }
        defaults.update(overrides)
        row = AffiliateProgram(**defaults)
        db_session.add(row)
        db_session.commit()
        db_session.refresh(row)
        return row

    return _make


@pytest.fixture()
def make_content_item(db_session: Session):
    """Factory for quickly creating ContentItem in tests."""

    def _make(**overrides: object) -> ContentItem:
        defaults = {
            "title": f"Test Content {uuid.uuid4().hex[:8]}",
            "body": "Test content.",
            "channel": "blog",
            "status": "draft",
        }
        defaults.update(overrides)
        row = ContentItem(**defaults)
        db_session.add(row)
        db_session.commit()
        db_session.refresh(row)
        return row

    return _make


@pytest.fixture()
def make_task(db_session: Session):
    """Factory for quickly creating AgentTask in tests."""

    def _make(**overrides: object) -> AgentTask:
        defaults = {
            "type": "generate_paragraph",
            "status": "queued",
            "input": {
                "prompt": "Write a paragraph about architecture skeleton."
            },
        }
        defaults.update(overrides)
        row = AgentTask(**defaults)
        db_session.add(row)
        db_session.commit()
        db_session.refresh(row)
        return row

    return _make


@pytest.fixture()
def real_session(db_engine: Engine) -> Generator[Session]:
    """Session with real commits to the test database.

    The Celery task (app.workers.tasks.generate_paragraph_task) opens
    ITS OWN session via `SessionLocal()` — meaning its own connection to
    the database. A row created by the transactional `db_session` (see above)
    would not be visible to it, because it never reaches the database (the
    SAVEPOINT is rolled back at the end of the test). Tests simulating the
    worker must therefore use this session so that the data really reaches
    Postgres.

    After the test, it cleans up all rows created in the affected tables —
    this is the only sensible way to clean up with real
    commits from a separate connection.
    """
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.query(ContentItem).delete()
        session.query(HitlDecision).delete()
        session.query(AffiliateProgram).delete()
        session.query(AgentTask).delete()
        session.commit()
        session.close()
