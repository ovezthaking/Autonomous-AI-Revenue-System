"""Trends agent test fixtures."""

pytest_plugins = ["revenue_swarm.testing.fixtures"]

import pytest  # noqa: E402
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
    monkeypatch.setattr("trends_agent.tasks.SessionLocal", lambda: proxy)
    return db_session
