"""API tests. Database fixtures come from the shared pytest plugin."""

pytest_plugins = ["revenue_swarm.testing.fixtures"]

from collections.abc import Generator  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402


@pytest.fixture(autouse=True)
def no_celery_broker(monkeypatch):
    """Replaces send_task so API tests do not need a live broker."""
    calls = []

    def _send_task(name, args=None, **kwargs):
        calls.append((str(name), list(args or [])))

    monkeypatch.setattr(
        "revenue_swarm.celery.celery_app.send_task", _send_task
    )
    return calls


@pytest.fixture()
def client(db_session: Session) -> Generator[TestClient]:
    """Client with get_db overridden by the transactional session."""
    from app.main import app
    from revenue_swarm.db import get_db

    def _override_get_db() -> Generator[Session]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_db, None)
