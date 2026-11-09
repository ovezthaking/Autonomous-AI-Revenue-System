import pytest

pytestmark = pytest.mark.integration


def test_rescore_returns_202_and_queues_research_task(
    client, no_celery_broker
):
    response = client.post("/research/rescore")

    assert response.status_code == 202
    assert response.json() == {"status": "queued"}
    assert no_celery_broker == [("research.rescore", [])]


def test_run_research_creates_task_and_queues_discover(
    client, no_celery_broker
):
    response = client.post("/research/run", json={"limit": 4})

    assert response.status_code == 202
    body = response.json()
    assert body["type"] == "research_programs"
    assert body["status"] == "queued"
    assert body["input"] == {"limit": 4}
    assert no_celery_broker == [("research.discover_programs", [body["id"]])]
