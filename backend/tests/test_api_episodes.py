from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy.orm import Session

from app.config import Settings
from app.models import Episode, User


@pytest.fixture
def with_keys(test_settings: Settings) -> None:
    test_settings.openai_api_key = SecretStr("sk-test")
    test_settings.elevenlabs_api_key = SecretStr("el-test")


@pytest.fixture
def with_interest(client: TestClient) -> None:
    client.post("/api/v1/interests", json={"kind": "catalog", "topic": "euroleague"})


def add_episode(session: Session, user: User, status: str, hours_ago: int = 0) -> Episode:
    episode = Episode(
        user_id=user.id,
        trigger="scheduled",
        status=status,
        scheduled_for=datetime.now(UTC) - timedelta(hours=hours_ago),
    )
    session.add(episode)
    session.flush()
    return episode


def test_generate_without_keys(client: TestClient, with_interest: None) -> None:
    response = client.post("/api/v1/episodes")

    assert response.status_code == 503
    assert "OPENAI_API_KEY and ELEVENLABS_API_KEY" in response.json()["detail"]


def test_generate_needs_an_interest(client: TestClient, with_keys: None) -> None:
    assert client.post("/api/v1/episodes").status_code == 409


def test_generate_queues_an_episode(
    client: TestClient, with_keys: None, with_interest: None
) -> None:
    response = client.post("/api/v1/episodes")

    assert response.status_code == 202
    assert response.json()["status"] == "queued"
    assert response.json()["trigger"] == "manual"


def test_double_click_queues_one_episode(
    client: TestClient, with_keys: None, with_interest: None
) -> None:
    client.post("/api/v1/episodes")

    assert client.post("/api/v1/episodes").status_code == 409
    assert len(client.get("/api/v1/episodes").json()["episodes"]) == 1


def test_list_is_paginated_newest_first(
    client: TestClient, session: Session, demo_user: User
) -> None:
    ids = [add_episode(session, demo_user, "completed", hours_ago=h).id for h in (48, 24, 0)]

    first = client.get("/api/v1/episodes", params={"page": 0, "limit": 2}).json()
    last = client.get("/api/v1/episodes", params={"page": 1, "limit": 2}).json()

    assert [e["id"] for e in first["episodes"]] == [ids[2], ids[1]]
    assert (first["page_count"], first["next_page"]) == (2, 1)
    assert [e["id"] for e in last["episodes"]] == [ids[0]]
    assert last["next_page"] is None


def test_empty_list(client: TestClient) -> None:
    assert client.get("/api/v1/episodes").json() == {
        "episodes": [],
        "page_count": 0,
        "next_page": None,
    }


def test_retry_a_failed_episode(
    client: TestClient, session: Session, demo_user: User, with_keys: None
) -> None:
    episode = add_episode(session, demo_user, "failed")
    episode.status_reason = "voice: timeout"

    response = client.post(f"/api/v1/episodes/{episode.id}/retry")

    assert response.status_code == 202
    assert response.json()["status"] == "queued"
    assert response.json()["status_reason"] is None


@pytest.mark.parametrize("status", ["skipped", "completed"])
def test_only_failed_episodes_can_be_retried(
    client: TestClient, session: Session, demo_user: User, with_keys: None, status: str
) -> None:
    episode = add_episode(session, demo_user, status)

    assert client.post(f"/api/v1/episodes/{episode.id}/retry").status_code == 409


def test_other_users_episode_is_not_found(client: TestClient, session: Session) -> None:
    other = User(email="other@example.com", name="Other")
    session.add(other)
    session.flush()
    episode = add_episode(session, other, "completed")

    assert client.get(f"/api/v1/episodes/{episode.id}").status_code == 404
