"""Shop agent test fixtures."""

pytest_plugins = ["revenue_swarm.testing.fixtures"]

from collections.abc import Generator  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402


class _UnclosableSessionProxy:
    def __init__(self, session: Session) -> None:
        self._session = session

    def close(self) -> None:
        pass

    def __getattr__(self, name: str):
        return getattr(self._session, name)


@pytest.fixture(autouse=True)
def no_celery_broker(monkeypatch: pytest.MonkeyPatch):
    """Captures send_task calls so tests do not require a live broker."""
    calls: list[tuple[str, list]] = []

    def _send_task(name, args=None, **kwargs):
        calls.append((str(name), list(args or [])))

    monkeypatch.setattr(
        "revenue_swarm.celery.celery_app.send_task", _send_task
    )
    return calls


@pytest.fixture()
def db(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> Session:
    proxy = _UnclosableSessionProxy(db_session)
    monkeypatch.setattr("shop_agent.tasks.SessionLocal", lambda: proxy)
    return db_session


@pytest.fixture()
def client(db: Session) -> Generator[TestClient]:
    from app.main import app
    from revenue_swarm.db import get_db

    def _override_get_db() -> Generator[Session]:
        yield db

    app.dependency_overrides[get_db] = _override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_db, None)
