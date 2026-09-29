from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy.orm import Session

from app.config import Settings
from app.models import Episode, User


@pytest.fixture
def with_keys(test_settings: Settings) -> None:
    test_settings.openai_api_key = SecretStr("sk-test")


def failed_episode(session: Session, synthetic: bool) -> Episode:
    user = User(email=f"fan{synthetic}@example.com", name="Fan", is_synthetic=synthetic)
    session.add(user)
    session.flush()
    episode = Episode(
        user_id=user.id,
        trigger="scheduled",
        scheduled_for=datetime(2026, 9, 29, 5, 0, tzinfo=UTC),
        status="failed",
        status_reason="voice: timeout",
    )
    session.add(episode)
    session.flush()
    return episode


def test_both_tabs_answer_with_their_blocks(client: TestClient) -> None:
    product = client.get("/api/v1/internal/product", params={"include_simulated": False})
    operations = client.get("/api/v1/internal/operations")

    assert product.status_code == operations.status_code == 200
    assert product.json()["include_simulated"] is False
    assert len(product.json()["weeks"]) == 8
    assert {
        "funnel",
        "activation",
        "depth",
        "topics",
        "cohorts",
        "delivery",
    } <= product.json().keys()
    assert operations.json()["include_simulated"] is True
    assert operations.json()["spend"]["daily_cap_usd"] == 1.0


def test_retry_requeues_real_runs_only(
    client: TestClient, session: Session, with_keys: None
) -> None:
    real, fake = failed_episode(session, False), failed_episode(session, True)

    queued = client.post(f"/api/v1/internal/episodes/{real.id}/retry")
    refused = client.post(f"/api/v1/internal/episodes/{fake.id}/retry")

    assert queued.status_code == 202 and queued.json()["status"] == "queued"
    assert refused.status_code == 409 and "Simulated" in refused.json()["detail"]
    assert session.get(Episode, fake.id).status == "failed"


def test_retry_needs_the_keys(client: TestClient, session: Session) -> None:
    real = failed_episode(session, False)

    assert client.post(f"/api/v1/internal/episodes/{real.id}/retry").status_code == 503


def test_retry_of_a_missing_episode_is_404(client: TestClient, with_keys: None) -> None:
    assert client.post("/api/v1/internal/episodes/999999/retry").status_code == 404
