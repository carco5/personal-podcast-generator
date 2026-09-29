from datetime import UTC, datetime, timedelta
from decimal import Decimal
from itertools import count

import pytest
from sqlalchemy.orm import Session

from app.config import Settings
from app.metrics import operations_metrics, product_metrics
from app.models import Episode, ListenEvent, ProviderCall, StageRun, User

NOW = datetime(2026, 9, 30, 12, 0, tzinfo=UTC)
MONDAY = datetime(2026, 9, 28, 0, 0, tzinfo=UTC)
DAY = timedelta(days=1)
UNIQUE = count(1)


def listener(session: Session, joined: datetime = NOW - 40 * DAY, synthetic: bool = False) -> User:
    user = User(
        email=f"fan{next(UNIQUE)}@example.com",
        name="Fan",
        created_at=joined,
        is_synthetic=synthetic,
    )
    session.add(user)
    session.flush()
    return user


def episode(
    session: Session,
    user: User,
    finished: datetime,
    duration: float = 300.0,
    chapters: list[dict] | None = None,
    status: str = "completed",
    trigger: str = "scheduled",
    scheduled: datetime | None = None,
    reason: str | None = None,
) -> Episode:
    done = status == "completed"
    row = Episode(
        user_id=user.id,
        status=status,
        trigger=trigger,
        scheduled_for=scheduled or finished - timedelta(seconds=next(UNIQUE)),
        created_at=finished - timedelta(minutes=10),
        started_at=finished - timedelta(minutes=5),
        finished_at=finished,
        attempts=1,
        audio_path="x.mp3" if done else None,
        duration_seconds=duration if done else None,
        chapters=(chapters or [{"key": "intro", "start": 0.5}]) if done else None,
        status_reason=None if done else (reason or "check: failed"),
    )
    session.add(row)
    session.flush()
    return row


def listen(session: Session, ep: Episode, start: datetime, *positions: float) -> None:
    session.add(ListenEvent(episode_id=ep.id, kind="play", position_seconds=0, created_at=start))
    for i, position in enumerate(positions, start=1):
        at = start + timedelta(seconds=15 * i)
        session.add(
            ListenEvent(
                episode_id=ep.id, kind="heartbeat", position_seconds=position, created_at=at
            )
        )
    session.flush()


def product(session: Session, include_simulated: bool = True):
    return product_metrics(session, NOW, include_simulated)


def test_repeats_and_skips_do_not_add_up(session: Session) -> None:
    user = listener(session)
    heard = NOW - 3 * DAY
    for positions in [(0, 0, 15, 15, 30), (0, 15, 30, 45), (0, 150)]:
        listen(session, episode(session, user, heard - DAY), heard, *positions)
    listen(session, episode(session, user, NOW - timedelta(hours=2)), NOW, 0, 15, 30, 45)

    funnel = product(session).funnel

    assert (funnel.generated, funnel.played, funnel.streamed, funnel.engaged) == (3, 3, 1, 0)


def test_engaged_is_40_percent_counting_the_short_last_slot(session: Session) -> None:
    user = listener(session)
    heard = NOW - 3 * DAY
    cases = [(100.0, (0, 15, 90)), (95.0, (0, 15, 90)), (180.0, (0, 15, 30, 45))]
    cases.append((180.0, (0, 15, 30, 45, 60)))
    for duration, positions in cases:
        listen(session, episode(session, user, heard - DAY, duration), heard, *positions)

    assert product(session).funnel.engaged == 2


def test_listens_count_once_in_the_week_they_cross_40_percent(session: Session) -> None:
    user = listener(session)
    early = episode(session, user, MONDAY - 2 * DAY, 60.0)
    late = episode(session, user, MONDAY - 2 * DAY, 60.0)
    listen(session, early, MONDAY - timedelta(seconds=90), 0, 15)
    listen(session, late, MONDAY - timedelta(seconds=15), 0, 15)
    listen(session, late, MONDAY + DAY, 0, 15, 30, 45)

    weeks = product(session).weeks

    assert len(weeks) == 8 and weeks[-1].week_start == MONDAY
    assert [(w.engaged_listens, w.engaged_listeners) for w in weeks[-2:]] == [(1, 1), (1, 1)]


def test_activation_is_the_first_episode_within_24_hours(session: Session) -> None:
    ready = NOW - 5 * DAY
    for hours in (23, 25):
        user = listener(session, joined=ready - DAY)
        first = episode(session, user, ready, 60.0)
        episode(session, user, ready + DAY, 60.0)
        listen(session, first, ready + timedelta(hours=hours), 0, 15, 30)
    newcomer = listener(session, joined=NOW - DAY)
    listen(session, episode(session, newcomer, NOW - timedelta(hours=2), 60.0), NOW, 0, 15)

    activation = product(session).activation

    assert (activation.new_listeners, activation.activated) == (2, 1)


def test_the_drop_off_curve_and_the_topics(session: Session) -> None:
    chapters = [
        {"key": "intro", "start": 0.5},
        {"key": "laliga", "start": 21.0},
        {"key": "nba", "start": 150.0},
        {"key": "closing", "start": 280.0},
    ]
    ep = episode(session, listener(session), NOW - 3 * DAY, 300.0, chapters)
    listen(session, ep, NOW - 2 * DAY, *range(0, 180, 15))

    metrics = product(session)

    curve = [point.listening for point in metrics.depth.drop_off]
    assert curve == [1, 1, 1, 1, 1, 1, 0, 0, 0, 0]
    assert metrics.depth.average_share_heard == pytest.approx(180 / 300)
    topics = {t.topic: (t.name, t.episodes, t.started, t.finished) for t in metrics.topics}
    assert topics == {"laliga": ("LaLiga", 1, 1, 1), "nba": ("NBA", 1, 1, 0)}


def test_cohorts_measure_week_1_and_week_4_once_reached(session: Session) -> None:
    for joined, days in [(NOW - 30 * DAY, (2, 22)), (NOW - 10 * DAY, (3,)), (NOW - 3 * DAY, (1,))]:
        user = listener(session, joined=joined)
        for day in days:
            ep = episode(session, user, joined + day * DAY - timedelta(hours=1), 60.0)
            listen(session, ep, joined + day * DAY, 0, 15)

    cohorts = product(session).cohorts

    totals = [sum(getattr(c, name) for c in cohorts) for name in ("listeners", "week1_eligible")]
    totals += [sum(getattr(c, name) for c in cohorts) for name in ("week1_retained",)]
    totals += [sum(getattr(c, n) for c in cohorts) for n in ("week4_eligible", "week4_retained")]
    assert totals == [3, 2, 2, 1, 1]


def test_on_time_counts_only_resolved_scheduled_episodes(session: Session) -> None:
    user = listener(session)
    due = NOW - 2 * DAY
    episode(session, user, due - timedelta(minutes=20), scheduled=due)
    episode(session, user, due + DAY + timedelta(minutes=5), scheduled=due + DAY)
    episode(session, user, due - 3 * DAY, status="failed", scheduled=due - 3 * DAY)
    episode(session, user, due - 4 * DAY, trigger="manual")
    episode(session, user, due - 5 * DAY, status="skipped", scheduled=due - 5 * DAY)

    delivery = product(session).delivery

    assert (delivery.due, delivery.on_time) == (3, 1)


def test_simulated_listeners_follow_the_switch(session: Session) -> None:
    real, fake = listener(session), listener(session, joined=NOW - 41 * DAY, synthetic=True)
    for user in (real, fake):
        listen(session, episode(session, user, NOW - 3 * DAY, 60.0), NOW - 2 * DAY, 0, 15)

    with_them, without = product(session, True), product(session, False)

    assert with_them.simulated_listeners == without.simulated_listeners == 1
    assert (with_them.funnel.engaged, without.funnel.engaged) == (2, 1)


def stage(
    session: Session,
    ep: Episode,
    name: str,
    seconds: float,
    status: str = "completed",
    calls: tuple[tuple[str, str, int | None], ...] = (),
    details: dict | None = None,
) -> None:
    start = ep.started_at
    run = StageRun(
        episode_id=ep.id,
        attempt=1,
        stage=name,
        status=status,
        started_at=start,
        finished_at=start + timedelta(seconds=seconds),
        details=details or {},
    )
    session.add(run)
    session.flush()
    for provider, cost, chars in calls:
        tokens = None if provider == "elevenlabs" else 100
        session.add(
            ProviderCall(
                stage_run_id=run.id,
                provider=provider,
                model="eleven_v3" if chars else "gpt-6-sol",
                input_tokens=tokens,
                output_tokens=tokens,
                characters=chars,
                cost_usd=Decimal(cost),
                latency_ms=1,
                created_at=start,
            )
        )
    session.flush()


def test_operations_add_up_costs_stages_and_failures(session: Session) -> None:
    now = NOW
    user = listener(session)
    done = episode(session, user, now - DAY)
    stage(session, done, "fetch", 10)
    stage(session, done, "select", 20, calls=(("openai", "0.04", None),))
    voice = {"voice": "eleven_v3", "reused_characters": 500}
    stage(session, done, "voice", 100, calls=(("elevenlabs", "0.10", 1000),), details=voice)
    failed = episode(session, user, now - 2 * DAY, status="failed", reason="check: unsupported")
    stage(session, failed, "check", 30, status="failed", calls=(("openai", "0.02", None),))
    capped = "Daily spending cap reached: $1.00 of $1.00 in the last 24 hours. Retry later."
    episode(session, user, now - 3 * DAY, status="failed", reason=capped)
    episode(session, user, now - 4 * DAY)
    fake = episode(session, listener(session, synthetic=True), now - DAY)
    stage(session, fake, "select", 99, calls=(("openai", "9.00", None),))
    config = Settings(_env_file=None, openai_api_key=None, worker_daily_budget_usd=Decimal(5))

    ops = operations_metrics(session, now, False, config)

    outcomes = ops.outcomes
    assert (outcomes.completed, outcomes.failed, outcomes.capped, outcomes.skipped) == (2, 1, 1, 0)
    assert (ops.cost.completed, ops.cost.openai_usd, ops.cost.elevenlabs_usd) == (1, 0.04, 0.10)
    assert (ops.voice_month.billed_characters, ops.voice_month.reused_characters) == (1000, 500)
    rows = {s.stage: (s.runs, s.failed, s.p50_seconds, s.cost_usd) for s in ops.stages}
    assert [s.stage for s in ops.stages] == ["fetch", "select", "check", "voice"]
    assert rows["select"] == (1, 0, 20.0, 0.04) and rows["check"] == (1, 1, None, 0.02)
    assert {(f.category, f.count) for f in ops.failures} == {("check", 1), ("spending cap", 1)}
    assert [run.id for run in ops.runs][:2] == [done.id, failed.id] and len(ops.runs) == 4
    assert [s.stage for s in ops.runs[0].stages] == ["fetch", "select", "voice"]
    assert ops.spend.daily_cap_usd == 5.0
