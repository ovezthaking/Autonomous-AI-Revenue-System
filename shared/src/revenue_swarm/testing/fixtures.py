"""Pytest fixtures shared by backend and agent packages.

Import this module before anything that reads configuration: the
environment variables below are applied at import time.
"""

import os

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
from sqlalchemy import event  # noqa: E402
from sqlalchemy.engine import Engine  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from revenue_swarm.config import DATABASE_URL  # noqa: E402
from revenue_swarm.db import Base, SessionLocal, engine  # noqa: E402
from revenue_swarm.models import (  # noqa: E402
    AffiliateProgram,
    AgentTask,
    ContentItem,
    HitlDecision,
)


def _ensure_database_exists(database_url: str) -> None:
    """Creates the test database if it does not already exist.

    Connects to the "postgres" database (maintenance db) with the same user
    and password as the rest of the application, just to execute
    `CREATE DATABASE`. Ignores the error if the database already exists.
    """
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
                pass


@pytest.fixture(scope="session")
def db_engine() -> Generator[Engine]:
    """Engine connected to the test database, with the schema created."""
    _ensure_database_exists(DATABASE_URL)
    Base.metadata.create_all(bind=engine)
    yield engine


@pytest.fixture()
def db_session(db_engine: Engine) -> Generator[Session]:
    """Session isolated by a transaction, rolled back after each test."""
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
    """Session with real commits, visible to a worker's own connection."""
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
