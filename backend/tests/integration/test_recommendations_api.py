import uuid

import pytest
from app.core.enums import ProgramStatus

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
