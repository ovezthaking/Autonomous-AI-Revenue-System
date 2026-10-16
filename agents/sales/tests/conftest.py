import pytest

pytest_plugins = ["revenue_swarm.testing.fixtures"]


class _UnclosableSessionProxy:
    def __init__(self, session):
        self._session = session

    def close(self) -> None:
        pass

    def __getattr__(self, name):
        return getattr(self._session, name)


@pytest.fixture(autouse=True)
def _bind_worker_session(db_session, monkeypatch):
    """Share the transactional db_session with sales_agent tasks in tests."""
    proxy = _UnclosableSessionProxy(db_session)
    monkeypatch.setattr("sales_agent.tasks.SessionLocal", lambda: proxy)
