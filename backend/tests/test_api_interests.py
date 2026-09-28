import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Interest, User


def test_add_catalog_and_custom_interests(client: TestClient) -> None:
    catalog = client.post("/api/v1/interests", json={"kind": "catalog", "topic": "euroleague"})
    custom = client.post(
        "/api/v1/interests",
        json={"kind": "custom", "topic": "Formula 1", "keywords": ["F1"], "weight": "low"},
    )

    assert catalog.status_code == 201
    assert catalog.json()["weight"] == "medium"
    assert catalog.json()["keywords"] == []
    assert custom.status_code == 201
    assert [i["topic"] for i in client.get("/api/v1/interests").json()] == [
        "euroleague",
        "Formula 1",
    ]


@pytest.mark.parametrize(
    "body",
    [
        {"kind": "catalog", "topic": "cricket"},
        {"kind": "catalog", "topic": "nba", "keywords": ["Lakers"]},
        {"kind": "custom", "topic": "Formula 1"},
        {"kind": "catalog", "topic": "nba", "weight": "huge"},
    ],
)
def test_invalid_interests_are_rejected(client: TestClient, body: dict) -> None:
    assert client.post("/api/v1/interests", json=body).status_code == 422


def test_duplicate_interest_conflicts(client: TestClient) -> None:
    body = {"kind": "catalog", "topic": "nba"}
    client.post("/api/v1/interests", json=body)

    assert client.post("/api/v1/interests", json=body).status_code == 409


def test_at_most_six_interests(client: TestClient) -> None:
    for topic in ["fc-barcelona", "euroleague", "liga-acb", "nba", "laliga", "champions-league"]:
        assert client.post("/api/v1/interests", json={"kind": "catalog", "topic": topic}).is_success

    response = client.post(
        "/api/v1/interests", json={"kind": "custom", "topic": "tennis", "keywords": ["Alcaraz"]}
    )

    assert response.status_code == 409


def test_change_weight_and_delete(client: TestClient) -> None:
    interest_id = client.post("/api/v1/interests", json={"kind": "catalog", "topic": "nba"}).json()[
        "id"
    ]

    patched = client.patch(f"/api/v1/interests/{interest_id}", json={"weight": "high"})
    deleted = client.delete(f"/api/v1/interests/{interest_id}")

    assert patched.json()["weight"] == "high"
    assert deleted.status_code == 204
    assert client.get("/api/v1/interests").json() == []


def test_other_users_interest_is_not_found(client: TestClient, session: Session) -> None:
    other = User(email="other@example.com", name="Other")
    session.add(other)
    session.flush()
    interest = Interest(user_id=other.id, kind="catalog", topic="nba", weight="low")
    session.add(interest)
    session.flush()

    assert (
        client.patch(f"/api/v1/interests/{interest.id}", json={"weight": "high"}).status_code == 404
    )
    assert client.delete(f"/api/v1/interests/{interest.id}").status_code == 404
