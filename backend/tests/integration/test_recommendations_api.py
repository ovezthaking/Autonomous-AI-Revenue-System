import uuid
from datetime import UTC, datetime, timedelta

import pytest
from revenue_swarm.enums import ProgramStatus

pytestmark = pytest.mark.integration


def test_create_recommendation_persists_as_proposed(client):
    response = client.post(
        "/recommendations",
        json={
            "name": "ACME SaaS Affiliate",
            "url": "https://acme.example/aff",
            "network": "ACME Network",
            "category": "SaaS",
            "rationale": "High EPC, monthly commission.",
            "extras": {"epc": 4.2},
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "ACME SaaS Affiliate"
    assert body["status"] == ProgramStatus.PROPOSED.value
    assert body["extras"] == {"epc": 4.2}
    assert body["score"] is None
    assert uuid.UUID(body["id"])


def test_create_recommendation_rejects_missing_name(client):
    response = client.post("/recommendations", json={})
    assert response.status_code == 422


def test_list_recommendations_defaults_to_proposed_only(client, make_program):
    proposed = make_program(status="proposed")
    make_program(status="approved")

    response = client.get("/recommendations")

    assert response.status_code == 200
    ids = [row["id"] for row in response.json()]
    assert str(proposed.id) in ids
    assert len(response.json()) == 1


def test_list_recommendations_orders_by_score_then_created_at(
    client, make_program
):
    now = datetime.now(UTC)
    older = make_program(
        name="Older tie",
        score=5,
        created_at=now - timedelta(hours=3),
    )
    missing = make_program(
        name="No score",
        score=None,
        created_at=now,
    )
    newer = make_program(
        name="Newer tie",
        score=5,
        created_at=now - timedelta(hours=1),
    )
    best = make_program(
        name="Best",
        score=20,
        created_at=now - timedelta(hours=2),
    )

    response = client.get("/recommendations")

    assert response.status_code == 200
    assert [row["name"] for row in response.json()] == [
        best.name,
        newer.name,
        older.name,
        missing.name,
    ]


def test_list_recommendations_with_empty_status_returns_everything(
    client, make_program
):
    make_program(status="proposed")
    make_program(status="approved")
    make_program(status="rejected")

    response = client.get("/recommendations", params={"status": ""})

    assert response.status_code == 200
    assert len(response.json()) == 3


def test_get_recommendation_returns_404_for_unknown_id(client):
    response = client.get(f"/recommendations/{uuid.uuid4()}")
    assert response.status_code == 404


def test_get_recommendation_returns_existing_program(client, make_program):
    program = make_program()
    response = client.get(f"/recommendations/{program.id}")
    assert response.status_code == 200
    assert response.json()["id"] == str(program.id)


def test_approve_recommendation_transitions_status(client, make_program):
    program = make_program(status="proposed")

    response = client.post(
        f"/recommendations/{program.id}/approve",
        json={"comment": "looks solid"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == ProgramStatus.APPROVED.value


def test_approve_recommendation_without_body_is_allowed(client, make_program):
    program = make_program(status="proposed")
    response = client.post(f"/recommendations/{program.id}/approve")
    assert response.status_code == 200
    assert response.json()["status"] == ProgramStatus.APPROVED.value


def test_reject_recommendation_transitions_status(client, make_program):
    program = make_program(status="proposed")
    response = client.post(f"/recommendations/{program.id}/reject")
    assert response.status_code == 200
    assert response.json()["status"] == ProgramStatus.REJECTED.value


def test_approve_already_decided_program_returns_409(client, make_program):
    program = make_program(status="approved")
    response = client.post(f"/recommendations/{program.id}/approve")
    assert response.status_code == 409


def test_reject_unknown_program_returns_404(client):
    response = client.post(f"/recommendations/{uuid.uuid4()}/reject")
    assert response.status_code == 404


def test_patch_metrics_stores_epc_without_dropping_extras(
    client, make_program
):
    program = make_program(
        extras={
            "source": "web",
            "facts": {"commission_type": "percent_recurring"},
        }
    )

    response = client.patch(
        f"/recommendations/{program.id}/metrics",
        json={"epc": 1.5},
    )

    assert response.status_code == 200
    extras = response.json()["extras"]
    assert extras["epc"] == 1.5
    assert extras["epc_source"] == "network_dashboard"
    assert extras["source"] == "web"
    assert extras["facts"]["commission_type"] == "percent_recurring"


def test_patch_metrics_rejects_non_positive_epc(client, make_program):
    program = make_program()
    response = client.patch(
        f"/recommendations/{program.id}/metrics",
        json={"epc": 0},
    )
    assert response.status_code == 422


def test_patch_metrics_unknown_program_returns_404(client):
    response = client.patch(
        f"/recommendations/{uuid.uuid4()}/metrics",
        json={"epc": 1.5},
    )
    assert response.status_code == 404
