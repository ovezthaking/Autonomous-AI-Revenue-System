import httpx
import pytest

pytest_plugins = ["revenue_swarm.testing.fixtures"]


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def _boom(*args, **kwargs):
        raise RuntimeError("Test tried to use the network")

    monkeypatch.setattr(httpx.Client, "send", _boom)
