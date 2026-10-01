import pytest

pytestmark = pytest.mark.integration


def test_rescore_returns_202_and_queues_research_task(
    client, no_celery_broker
):
    response = client.post("/research/rescore")

    assert response.status_code == 202
    assert response.json() == {"status": "queued"}
    assert no_celery_broker == [("research.rescore", [])]
