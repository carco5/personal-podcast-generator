from datetime import UTC, datetime, time, timedelta

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Episode, Interest, PodcastSettings, User


def make_user(session: Session, email: str = "listener@example.com") -> User:
    user = User(email=email, name="Listener")
    session.add(user)
    session.flush()
    return user


@pytest.mark.parametrize(
    ("row", "field", "bad_value"),
    [
        ("episode", "status", "done"),
        ("episode", "trigger", "api"),
        ("settings", "length_minutes", 4),
        ("settings", "tone", "funny"),
        ("interest", "weight", "huge"),
        ("interest", "keywords", ["euroleague"]),
    ],
)
def test_check_constraints_reject_bad_values(
    session: Session, row: str, field: str, bad_value: object
) -> None:
    user = make_user(session)
    rows = {
        "episode": Episode(user_id=user.id, trigger="manual", scheduled_for=func.now()),
        "settings": PodcastSettings(
            user_id=user.id,
            show_name="Show",
            length_minutes=5,
            tone="casual",
            hosts=[],
            schedule_days=[],
            schedule_time=time(7, 0),
            timezone="UTC",
        ),
        "interest": Interest(user_id=user.id, kind="catalog", topic="euroleague", weight="high"),
    }
    setattr(rows[row], field, bad_value)
    session.add(rows[row])
    with pytest.raises(IntegrityError):
        session.flush()


def test_one_episode_in_flight_per_user(session: Session) -> None:
    user = make_user(session)
    now = datetime.now(UTC)
    session.add(Episode(user_id=user.id, trigger="manual", scheduled_for=now, status="completed"))
    session.add(Episode(user_id=user.id, trigger="scheduled", scheduled_for=now + timedelta(1)))
    session.flush()

    session.add(Episode(user_id=user.id, trigger="manual", scheduled_for=now + timedelta(2)))
    with pytest.raises(IntegrityError, match="uq_episodes_one_in_flight_per_user"):
        session.flush()


def test_deleting_a_user_deletes_their_rows(session: Session) -> None:
    user = make_user(session)
    session.add(Interest(user_id=user.id, kind="catalog", topic="nba", weight="low"))
    session.add(Episode(user_id=user.id, trigger="manual", scheduled_for=func.now()))
    session.flush()

    session.delete(user)
    session.flush()

    assert session.scalars(select(Interest)).all() == []
    assert session.scalars(select(Episode)).all() == []
