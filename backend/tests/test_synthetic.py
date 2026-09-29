from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Episode, ListenEvent, StageRun, User
from app.synthetic import (
    EMAIL_DOMAIN,
    build,
    delete_synthetic,
    seed_if_missing,
    seed_synthetic,
)

NOW = datetime(2026, 9, 29, 21, 0, tzinfo=UTC)
STAGES = ["fetch", "select", "write", "check", "voice", "master"]


def test_the_data_is_deterministic() -> None:
    assert build(NOW) == build(NOW)
    assert build(NOW, seed=1) != build(NOW)


def test_the_data_follows_the_products_rules() -> None:
    users = build(NOW)
    episodes = [ep for user in users for ep in user.episodes]
    assert len(users) == 69 and len(episodes) > 1000
    cost = 0.0
    for user in users:
        assert user.email.endswith(f"@{EMAIL_DOMAIN}") and user.created_at <= NOW
        for ep in user.episodes:
            row = ep.row
            assert user.created_at < row["scheduled_for"] <= NOW
            assert row["status"] in {"completed", "failed", "skipped"}
            assert (row["status"] == "completed") == ("audio_path" in row)
            assert (row["status"] != "completed") == ("status_reason" in row)
            clock = row["started_at"]
            for stage in ep.stages:
                assert clock <= stage.started_at <= stage.finished_at <= row["finished_at"]
                clock = stage.finished_at
                cost += sum(call["cost_usd"] for call in stage.calls)
            if row["status"] == "completed":
                assert [stage.stage for stage in ep.stages] == STAGES
                starts = [chapter["start"] for chapter in row["chapters"]]
                assert starts[0] == 0.5 and starts == sorted(starts)
                assert starts[-1] < row["duration_seconds"]
            if ep.events:
                assert ep.events[0][:2] == ("play", 0.0)
            for kind, position, created in ep.events:
                assert created <= NOW
                if kind == "heartbeat":
                    assert position % 15 == 0 and position < row["duration_seconds"]
    completed = sum(ep.row["status"] == "completed" for ep in episodes)
    assert 0.35 < cost / completed < 0.55


def test_seeding_writes_every_row_and_deleting_keeps_real_users(
    session: Session, demo_user: User
) -> None:
    users = build(NOW)

    created = seed_synthetic(session, NOW)

    def count(table: type, *where: object) -> int:
        return session.scalar(select(func.count()).select_from(table).where(*where))

    assert created == len(users) == count(User, User.is_synthetic)
    assert count(Episode) == sum(len(u.episodes) for u in users)
    assert count(ListenEvent) == sum(len(ep.events) for u in users for ep in u.episodes)
    assert seed_if_missing(session, NOW) == 0

    delete_synthetic(session)

    assert count(User) == 1 and session.get(User, demo_user.id) is not None
    assert count(Episode) == count(StageRun) == count(ListenEvent) == 0
