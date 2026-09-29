from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import Settings
from app.demo import SAMPLE_AUDIO, ensure_demo_user, seed_demo_listener
from app.models import Episode, Interest, User


@pytest.fixture
def seeded(session: Session, test_settings: Settings, tmp_path: Path) -> User:
    test_settings.data_dir = tmp_path
    return seed_demo_listener(session, tmp_path)


def test_a_fresh_database_starts_with_the_sample(
    seeded: User, client: TestClient, tmp_path: Path
) -> None:
    settings = client.get("/api/v1/settings").json()
    interests = [i["topic"] for i in client.get("/api/v1/interests").json()]
    (episode,) = client.get("/api/v1/episodes").json()["episodes"]
    detail = client.get(f"/api/v1/episodes/{episode['id']}").json()
    audio = client.get(f"/api/v1/episodes/{episode['id']}/audio")

    assert (settings["show_name"], settings["length_minutes"]) == ("Barça & Beyond", 5)
    chapters = [chapter["key"] for chapter in detail["chapters"]]
    assert chapters == ["intro", *interests, "closing"]
    assert (episode["status"], episode["news_as_of"]) == ("completed", "2026-09-28T21:32:30Z")
    assert episode["title"] == "Barça One Win from Matching Their Best Start"
    assert not any("[" in turn["text"] for s in detail["transcript"] for turn in s["turns"])
    assert detail["sources"] and all(s["url"].startswith("https://") for s in detail["sources"])
    assert audio.status_code == 200 and audio.content == SAMPLE_AUDIO.read_bytes()


def test_seeding_twice_changes_nothing(seeded: User, session: Session, tmp_path: Path) -> None:
    again = seed_demo_listener(session, tmp_path)

    assert again.id == seeded.id
    assert session.scalar(select(func.count()).select_from(Interest)) == 7
    assert session.scalar(select(func.count()).select_from(Episode)) == 1


def test_an_existing_demo_user_is_left_alone(session: Session, tmp_path: Path) -> None:
    user = ensure_demo_user(session)

    assert seed_demo_listener(session, tmp_path).id == user.id
    assert session.scalar(select(func.count()).select_from(Interest)) == 0
    assert not (tmp_path / "demo").exists()
