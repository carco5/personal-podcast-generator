from datetime import UTC, datetime

from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.config import Settings


def test_without_keys_or_interests(client: TestClient) -> None:
    assert client.get("/api/v1/generation").json() == {
        "missing_keys": ["OPENAI_API_KEY"],
        "voice": "tone",
        "next_episode_at": None,
    }


def test_real_voice_needs_elevenlabs_too(client: TestClient, test_settings: Settings) -> None:
    test_settings.worker_voice = "elevenlabs"
    test_settings.openai_api_key = SecretStr("sk-test")

    body = client.get("/api/v1/generation").json()

    assert (body["missing_keys"], body["voice"]) == (["ELEVENLABS_API_KEY"], "elevenlabs")


def test_next_episode_is_the_next_scheduled_time(client: TestClient) -> None:
    client.post("/api/v1/interests", json={"kind": "catalog", "topic": "nba"})

    next_at = datetime.fromisoformat(client.get("/api/v1/generation").json()["next_episode_at"])

    assert 0 < (next_at - datetime.now(UTC)).total_seconds() <= 24 * 3600
    assert next_at.astimezone().utcoffset() is not None
