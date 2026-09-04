import pytest
from app.core.config import getenv


def test_getenv_returns_value_set_in_environment(monkeypatch):
    monkeypatch.setenv("SOME_TEST_VAR", "hello")
    assert getenv("SOME_TEST_VAR") == "hello"


def test_getenv_falls_back_to_default_when_unset(monkeypatch):
    monkeypatch.delenv("SOME_MISSING_VAR", raising=False)
    assert getenv("SOME_MISSING_VAR", "default-value") == "default-value"


def test_getenv_raises_when_missing_and_no_default(monkeypatch):
    monkeypatch.delenv("SOME_MISSING_VAR", raising=False)
    with pytest.raises(RuntimeError, match="SOME_MISSING_VAR"):
        getenv("SOME_MISSING_VAR")


def test_getenv_prefers_environment_over_default(monkeypatch):
    monkeypatch.setenv("SOME_TEST_VAR", "from-env")
    assert getenv("SOME_TEST_VAR", "from-default") == "from-env"
