import shutil
import threading
import time
from contextlib import nullcontext
from datetime import UTC, datetime, timedelta
from datetime import time as clock
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import Engine, delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app import worker
from app.config import Settings
from app.models import Episode, PodcastSettings, ProviderCall, StageRun, User
from app.pipeline import fetch
from app.pipeline.voice import ToneVoice
from app.worker import (
    INTERRUPTED,
    Shutdown,
    claim_next,
    process_next,
    recover_stale,
    schedule_due,
    spent_in_window,
    tick,
)
from tests.fakes import FakeLlm, make_article, make_listener

NOW = datetime(2026, 9, 29, 10, 0, tzinfo=UTC)
SEVEN_AM_MADRID = datetime(2026, 9, 29, 5, 0, tzinfo=UTC)


@pytest.fixture(autouse=True)
def no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(fetch, "episode_sources", lambda run: {})


def scheduled_listener(session: Session, interests: bool = True) -> PodcastSettings:
    _, podcast, _ = make_listener(session, [("euroleague", "high")] if interests else [])
    podcast.schedule_days = [1, 2, 3, 4, 5, 6, 7]
    podcast.updated_at = NOW - timedelta(days=2)
    session.flush()
    return podcast


def episodes_of(session: Session, user_id: int) -> list[tuple[str, datetime, str]]:
    rows = session.scalars(select(Episode).where(Episode.user_id == user_id).order_by(Episode.id))
    return [(row.trigger, row.scheduled_for, row.status) for row in rows]


def test_the_latest_slot_is_queued_once(session: Session) -> None:
    podcast = scheduled_listener(session)

    assert schedule_due(session, NOW) == 1
    assert schedule_due(session, NOW) == 0
    assert episodes_of(session, podcast.user_id) == [("scheduled", SEVEN_AM_MADRID, "queued")]


def test_old_slots_and_slots_before_saving_are_not_caught_up(session: Session) -> None:
    podcast = scheduled_listener(session)
    assert schedule_due(session, SEVEN_AM_MADRID + timedelta(hours=13)) == 0

    podcast.updated_at = SEVEN_AM_MADRID + timedelta(hours=1)
    session.flush()
    assert schedule_due(session, NOW) == 0
    assert schedule_due(session, NOW + timedelta(days=1)) == 1


def test_the_episode_is_queued_30_minutes_before_its_time(session: Session) -> None:
    podcast = scheduled_listener(session)

    assert schedule_due(session, SEVEN_AM_MADRID - timedelta(minutes=31)) == 0
    assert schedule_due(session, SEVEN_AM_MADRID - timedelta(minutes=29)) == 1
    assert episodes_of(session, podcast.user_id) == [("scheduled", SEVEN_AM_MADRID, "queued")]


def test_a_schedule_two_minutes_ahead_is_queued_at_once(session: Session) -> None:
    podcast = scheduled_listener(session)
    podcast.schedule_time, podcast.updated_at = clock(12, 2), NOW
    session.flush()

    assert schedule_due(session, NOW) == 1
    assert episodes_of(session, podcast.user_id) == [
        ("scheduled", NOW + timedelta(minutes=2), "queued")
    ]


def test_listeners_without_interests_are_not_scheduled(session: Session) -> None:
    podcast = scheduled_listener(session, interests=False)

    assert schedule_due(session, NOW) == 0
    assert episodes_of(session, podcast.user_id) == []


def test_an_episode_in_flight_delays_the_scheduled_one(session: Session) -> None:
    podcast = scheduled_listener(session)
    manual = Episode(user_id=podcast.user_id, trigger="manual", scheduled_for=NOW)
    session.add(manual)
    session.flush()

    assert schedule_due(session, NOW) == 0

    manual.status, manual.audio_path = "completed", "episodes/manual.mp3"
    session.flush()
    assert schedule_due(session, NOW + timedelta(minutes=5)) == 1


def test_on_conflict_do_nothing_covers_the_in_flight_index(session: Session) -> None:
    podcast = scheduled_listener(session)
    session.add(Episode(user_id=podcast.user_id, trigger="manual", scheduled_for=NOW))
    session.flush()

    statement = insert(Episode).values(
        user_id=podcast.user_id, trigger="scheduled", scheduled_for=SEVEN_AM_MADRID
    )
    inserted = statement.on_conflict_do_nothing().returning(Episode.id)
    assert session.scalars(inserted).all() == []


def test_stale_episodes_are_failed_and_fresh_ones_are_kept(
    session: Session, demo_user: User
) -> None:
    podcast = scheduled_listener(session)
    stale = Episode(
        user_id=podcast.user_id,
        trigger="scheduled",
        scheduled_for=NOW - timedelta(hours=1),
        status="in_progress",
        started_at=NOW - timedelta(minutes=31),
        attempts=1,
    )
    fresh = Episode(
        user_id=demo_user.id,
        trigger="manual",
        scheduled_for=NOW,
        status="in_progress",
        started_at=NOW - timedelta(minutes=5),
        attempts=1,
    )
    session.add_all([stale, fresh])
    session.flush()
    session.add(StageRun(episode_id=stale.id, attempt=1, stage="write", status="in_progress"))
    session.flush()

    assert recover_stale(session, NOW) == [stale.id]
    assert (stale.status, stale.status_reason) == ("failed", INTERRUPTED)
    assert fresh.status == "in_progress"
    stage = session.scalars(select(StageRun).where(StageRun.episode_id == stale.id)).one()
    assert (stage.status, stage.error) == ("failed", "interrupted")


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg is not installed")
def test_a_tick_schedules_and_generates_the_episode(session: Session, tmp_path: Path) -> None:
    podcast = scheduled_listener(session)
    make_article(session, "eurohoops-euroleague", "Big signing", NOW - timedelta(hours=2))
    config = Settings(_env_file=None, openai_api_key=None, data_dir=tmp_path)

    episode = tick(session, config, llm=FakeLlm(), voice=ToneVoice(), now=NOW)

    assert episode is not None and episode.trigger == "scheduled"
    assert episode.status == "completed" and (tmp_path / episode.audio_path).exists()
    assert tick(session, config, llm=FakeLlm(), voice=ToneVoice(), now=NOW) is None
    assert episodes_of(session, podcast.user_id) == [("scheduled", SEVEN_AM_MADRID, "completed")]


def spend(session: Session, user: User, usd: str, at: datetime) -> None:
    episode = Episode(
        user_id=user.id,
        trigger="manual",
        scheduled_for=at,
        status="failed",
        status_reason="Test reason",
    )
    session.add(episode)
    session.flush()
    stage = StageRun(episode_id=episode.id, attempt=1, stage="write", status="completed")
    session.add(stage)
    session.flush()
    session.add(
        ProviderCall(
            stage_run_id=stage.id,
            provider="openai",
            model="gpt-6-sol",
            input_tokens=1,
            output_tokens=1,
            cost_usd=Decimal(usd),
            latency_ms=1,
            created_at=at,
        )
    )
    session.flush()


def test_the_daily_cap_fails_the_episode_before_spending(
    session: Session, demo_user: User, tmp_path: Path
) -> None:
    spend(session, demo_user, "0.40", NOW - timedelta(hours=25))
    spend(session, demo_user, "1.00", NOW - timedelta(hours=1))
    podcast = scheduled_listener(session)
    queued = Episode(user_id=podcast.user_id, trigger="manual", scheduled_for=NOW)
    session.add(queued)
    session.flush()
    llm = FakeLlm()
    config = Settings(_env_file=None, openai_api_key=None, data_dir=tmp_path)

    assert spent_in_window(session, NOW) == Decimal("1.00")
    episode = process_next(session, config, llm=llm, voice=ToneVoice(), now=NOW)

    assert episode is queued and episode.status == "failed"
    assert episode.status_reason == (
        "Daily spending cap reached: $1.00 of $1.00 in the last 24 hours. Retry later."
    )
    assert episode.attempts == 0 and llm.prompts == []
    assert session.scalars(select(StageRun).where(StageRun.episode_id == queued.id)).all() == []


def test_two_workers_never_claim_the_same_episode(engine: Engine) -> None:
    with Session(engine) as setup:
        users = [User(email=f"skip-locked-{n}@example.com", name="Worker test") for n in (1, 2)]
        setup.add_all(users)
        setup.flush()
        setup.add_all(
            Episode(user_id=user.id, trigger="manual", scheduled_for=NOW) for user in users
        )
        setup.commit()
        user_ids = [user.id for user in users]
    try:
        with Session(engine) as first, Session(engine) as second, Session(engine) as third:
            one, two = claim_next(first), claim_next(second)
            assert one is not None and two is not None and one.id != two.id
            started = time.monotonic()
            assert claim_next(third) is None
            assert time.monotonic() - started < 1
    finally:
        with Session(engine) as cleanup:
            cleanup.execute(delete(User).where(User.id.in_(user_ids)))
            cleanup.commit()


def run_loop(
    session: Session,
    monkeypatch: pytest.MonkeyPatch,
    shutdown: Shutdown,
    on_tick: object,
    config: Settings | None = None,
) -> list[bool]:
    ingests: list[bool] = []
    monkeypatch.setattr(worker, "tick", on_tick)
    monkeypatch.setattr(worker, "ingest_catalogue", lambda session, config: ingests.append(True))
    worker.run_forever(
        config or Settings(_env_file=None),
        llm=FakeLlm(),
        voice=ToneVoice(),
        shutdown=shutdown,
        session_factory=lambda: nullcontext(session),
    )
    return ingests


def test_the_loop_ingests_at_start_and_stops_while_waiting(
    session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    shutdown = Shutdown()
    config = Settings(_env_file=None, worker_poll_seconds=60)
    threading.Timer(0.2, shutdown.request, args=(15, None)).start()

    started = time.monotonic()
    ingests = run_loop(session, monkeypatch, shutdown, lambda *args, **kwargs: None, config)

    assert ingests == [True] and time.monotonic() - started < 2


def test_a_stop_during_an_episode_starts_no_new_work(
    session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    shutdown = Shutdown()

    def busy_tick(*args: object, **kwargs: object) -> None:
        shutdown.request(15, None)

    assert run_loop(session, monkeypatch, shutdown, busy_tick) == []


def test_an_error_does_not_stop_the_worker(
    session: Session, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    shutdown = Shutdown()
    calls: list[int] = []

    def flaky_tick(*args: object, **kwargs: object) -> None:
        calls.append(1)
        if len(calls) == 1:
            raise RuntimeError("database restarting")
        shutdown.request(15, None)

    monkeypatch.setattr(worker, "tick", flaky_tick)
    monkeypatch.setattr(worker, "ingest_catalogue", lambda session, config: None)
    monkeypatch.setattr(Shutdown, "sleep", lambda self, seconds: None)

    worker.run_forever(
        Settings(_env_file=None),
        llm=FakeLlm(),
        voice=ToneVoice(),
        shutdown=shutdown,
        session_factory=lambda: nullcontext(session),
    )

    assert len(calls) == 2 and "database restarting" in caplog.text


def test_the_worker_needs_the_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    config = Settings(
        _env_file=None, openai_api_key=None, elevenlabs_api_key=None, worker_voice="elevenlabs"
    )
    monkeypatch.setattr(worker, "get_settings", lambda: config)

    with pytest.raises(SystemExit, match="OPENAI_API_KEY and ELEVENLABS_API_KEY"):
        worker.main()


def simulated(session: Session, podcast: PodcastSettings) -> User:
    user = session.get_one(User, podcast.user_id)
    user.is_synthetic = True
    session.flush()
    return user


def test_a_simulated_listener_is_never_scheduled(session: Session) -> None:
    simulated(session, scheduled_listener(session))

    assert schedule_due(session, NOW) == 0


def test_a_simulated_episode_is_never_claimed(session: Session) -> None:
    user = simulated(session, scheduled_listener(session))
    session.add(Episode(user_id=user.id, trigger="manual", scheduled_for=NOW))
    session.flush()

    assert claim_next(session) is None


def test_simulated_costs_do_not_count_towards_the_cap(session: Session, demo_user: User) -> None:
    spend(session, demo_user, "0.30", NOW - timedelta(hours=1))
    spend(session, simulated(session, scheduled_listener(session)), "50.00", NOW)

    assert spent_in_window(session, NOW) == Decimal("0.30")
