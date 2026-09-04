import uuid

import app.api.tasks as tasks_api
import pytest

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def no_celery_broker(monkeypatch):
    """Replaces .delay() with a mock.

    The POST /tasks endpoint sends a task to Celery (Redis) in the background.
    API tests should not depend on whether the broker is actually alive — the
    execution of the task itself is tested separately, directly, in
    tests/integration/test_worker_task.py.
    """
    calls = []
    monkeypatch.setattr(
        tasks_api.generate_paragraph_task,
        "delay",
        lambda task_id: calls.append(task_id),
    )
    return calls


def test_create_task_returns_202_and_queues_it(client, no_celery_broker):
    response = client.post("/tasks", json={"prompt": "Describe Redis."})

    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "queued"
    assert body["type"] == "generate_paragraph"
    assert body["input"] == {"prompt": "Describe Redis."}
    assert body["output"] is None
    assert body["error"] is None
    assert no_celery_broker == [body["id"]]


def test_create_task_uses_default_prompt_when_omitted(client):
    response = client.post("/tasks", json={})
    assert response.status_code == 202
    assert "walking skeleton" in response.json()["input"]["prompt"].lower()


def test_get_task_returns_existing_task(client, make_task):
    task = make_task(input={"prompt": "test"})
    response = client.get(f"/tasks/{task.id}")
    assert response.status_code == 200
    assert response.json()["id"] == str(task.id)


def test_get_task_returns_404_for_unknown_id(client):
    response = client.get(f"/tasks/{uuid.uuid4()}")
    assert response.status_code == 404
