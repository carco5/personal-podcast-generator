from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import Settings
from app.models import Episode, EpisodeArticle, ListenEvent, StageRun, User
from tests.fakes import make_article

MONDAY = datetime(2026, 9, 28, 21, 30, tzinfo=UTC)


def completed_episode(session: Session, user: User) -> Episode:
    episode = Episode(
        user_id=user.id,
        trigger="manual",
        status="completed",
        scheduled_for=MONDAY,
        title="Barça one win from their best start",
        audio_path="episodes/test.mp3",
        duration_seconds=12.5,
        chapters=[{"key": "intro", "start": 0.5}, {"key": "fc-barcelona-football", "start": 4.0}],
        plan={"selected_at": "2026-09-28T21:32:30+00:00"},
        script={
            "title": "Barça one win from their best start",
            "segments": [
                {
                    "key": "intro",
                    "turns": [
                        {"speaker": "host", "text": "[excited]  Welcome back.", "source_ids": []}
                    ],
                },
                {
                    "key": "fc-barcelona-football",
                    "turns": [
                        {"speaker": "analyst", "text": "Seven wins.", "source_ids": ["S10", "S1"]}
                    ],
                },
            ],
        },
    )
    session.add(episode)
    session.flush()
    for source_id, source in (("S1", "laliga-data"), ("S2", "uefa-news"), ("S10", "fcbarcelona")):
        meta = {"type": "result"} if source == "laliga-data" else None
        article = make_article(session, source, f"Title {source_id}", MONDAY, meta=meta)
        session.add(
            EpisodeArticle(
                episode_id=episode.id,
                article_id=article.id,
                source_id=source_id,
                block="fc-barcelona-football",
                rank=1,
            )
        )
    session.flush()
    return episode


def test_detail_has_chapters_readable_script_and_cited_sources(
    client: TestClient, session: Session, demo_user: User
) -> None:
    episode = completed_episode(session, demo_user)

    detail = client.get(f"/api/v1/episodes/{episode.id}").json()

    assert [(c["title"], c["start_seconds"]) for c in detail["chapters"]] == [
        ("Intro", 0.5),
        ("FC Barcelona football", 4.0),
    ]
    intro, football = detail["transcript"]
    assert intro["turns"][0]["text"] == "Welcome back."
    assert football["title"] == "FC Barcelona football"
    assert [(s["source_id"], s["outlet"], s["kind"]) for s in detail["sources"]] == [
        ("S1", "LaLiga", "data"),
        ("S10", "FC Barcelona", "article"),
    ]
    assert detail["title"] == "Barça one win from their best start"
    assert detail["duration_seconds"] == 12.5
    assert datetime.fromisoformat(detail["news_as_of"]) == datetime(
        2026, 9, 28, 21, 32, 30, tzinfo=UTC
    )


def test_detail_of_a_queued_episode_is_empty(
    client: TestClient, session: Session, demo_user: User
) -> None:
    episode = Episode(user_id=demo_user.id, trigger="manual", scheduled_for=MONDAY)
    session.add(episode)
    session.flush()

    detail = client.get(f"/api/v1/episodes/{episode.id}").json()

    assert (detail["chapters"], detail["transcript"], detail["sources"]) == ([], [], [])


def test_audio_is_served_whole_and_in_ranges(
    client: TestClient, session: Session, demo_user: User, test_settings: Settings, tmp_path: Path
) -> None:
    episode = completed_episode(session, demo_user)
    test_settings.data_dir = tmp_path
    (tmp_path / "episodes").mkdir()
    (tmp_path / "episodes" / "test.mp3").write_bytes(bytes(1000))
    url = f"/api/v1/episodes/{episode.id}/audio"

    whole = client.get(url)
    part = client.get(url, headers={"Range": "bytes=0-99"})

    assert whole.status_code == 200 and whole.headers["content-type"] == "audio/mpeg"
    assert whole.headers["content-disposition"].startswith("inline")
    assert part.status_code == 206 and len(part.content) == 100
    assert part.headers["content-range"] == "bytes 0-99/1000"
    (tmp_path / "episodes" / "test.mp3").unlink()
    assert client.get(url).json() == {"detail": "The audio file is missing"}


def test_listen_events_are_recorded_for_completed_episodes(
    client: TestClient, session: Session, demo_user: User
) -> None:
    episode = completed_episode(session, demo_user)
    queued = Episode(user_id=demo_user.id, trigger="manual", scheduled_for=datetime.now(UTC))
    session.add(queued)
    session.flush()
    url = f"/api/v1/episodes/{episode.id}/listen-events"

    assert client.post(url, json={"kind": "play", "position_seconds": 0}).status_code == 204
    assert client.post(url, json={"kind": "heartbeat", "position_seconds": 15}).status_code == 204
    assert client.post(url, json={"kind": "pause", "position_seconds": 1}).status_code == 422
    assert client.post(url, json={"kind": "play", "position_seconds": -1}).status_code == 422
    other = f"/api/v1/episodes/{queued.id}/listen-events"
    assert client.post(other, json={"kind": "play", "position_seconds": 0}).status_code == 409
    rows = session.scalars(select(ListenEvent).where(ListenEvent.episode_id == episode.id)).all()
    assert [(row.kind, row.position_seconds) for row in rows] == [("play", 0), ("heartbeat", 15)]


def test_listen_events_of_another_user_are_not_found(client: TestClient, session: Session) -> None:
    stranger = User(email="stranger@example.com", name="Stranger")
    session.add(stranger)
    session.flush()
    episode = completed_episode(session, stranger)

    response = client.post(
        f"/api/v1/episodes/{episode.id}/listen-events", json={"kind": "play", "position_seconds": 0}
    )

    assert response.status_code == 404
    assert session.scalar(select(func.count()).select_from(ListenEvent)) == 0


def test_the_list_shows_the_running_stage(
    client: TestClient, session: Session, demo_user: User
) -> None:
    completed_episode(session, demo_user)
    running = Episode(
        user_id=demo_user.id,
        trigger="manual",
        status="in_progress",
        scheduled_for=datetime.now(UTC),
    )
    session.add(running)
    session.flush()
    session.add(StageRun(episode_id=running.id, attempt=1, stage="write", status="in_progress"))
    session.flush()

    episodes = client.get("/api/v1/episodes").json()["episodes"]

    assert [(e["status"], e["stage"]) for e in episodes] == [
        ("in_progress", "write"),
        ("completed", None),
    ]


@pytest.mark.parametrize("status", ["queued", "failed"])
def test_no_audio_yet(client: TestClient, session: Session, demo_user: User, status: str) -> None:
    episode = Episode(
        user_id=demo_user.id,
        trigger="manual",
        status=status,
        scheduled_for=datetime.now(UTC),
        status_reason="Test reason" if status == "failed" else None,
    )
    session.add(episode)
    session.flush()

    response = client.get(f"/api/v1/episodes/{episode.id}/audio")

    assert response.json() == {"detail": "This episode has no audio yet"}
