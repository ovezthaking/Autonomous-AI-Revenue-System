import uuid

import pytest

pytestmark = pytest.mark.integration


def test_create_task_returns_202_and_queues_it(client, no_celery_broker):
    response = client.post("/tasks", json={"prompt": "Describe Redis."})

    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "queued"
    assert body["type"] == "generate_paragraph"
    assert body["input"] == {"prompt": "Describe Redis."}
    assert body["output"] is None
    assert body["error"] is None
    assert no_celery_broker == [("generate_paragraph", [body["id"]])]


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


def test_list_tasks_returns_recent_tasks(client, make_task):
    t1 = make_task(input={"prompt": "one"})
    t2 = make_task(input={"prompt": "two"})
    response = client.get("/tasks", params={"limit": 5})
    assert response.status_code == 200
    ids = {row["id"] for row in response.json()}
    assert {str(t1.id), str(t2.id)} <= ids
