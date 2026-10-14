import pytest

pytest_plugins = ["revenue_swarm.testing.fixtures"]


@pytest.fixture(autouse=True)
def no_celery_broker(monkeypatch):
    """Captures send_task calls so tests do not require a live broker."""
    calls: list[tuple[str, list]] = []

    def _send_task(name, args=None, **kwargs):
        calls.append((str(name), list(args or [])))

    monkeypatch.setattr(
        "revenue_swarm.celery.celery_app.send_task", _send_task
    )
    return calls


@pytest.fixture
def db(real_session):
    """Real session so tasks opening SessionLocal() see committed rows."""
    return real_session
