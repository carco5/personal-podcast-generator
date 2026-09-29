"""Simulated listeners for the internal dashboard: deterministic and calibrated on real runs."""

import argparse
import math
import random
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import delete, insert, select
from sqlalchemy.orm import Session

from app.catalog import CATALOG, SPORTS
from app.db import engine
from app.models import Episode, ListenEvent, ProviderCall, StageRun, User
from app.pipeline.llm import PRICES
from app.pipeline.selection import CHARS_PER_SECOND
from app.pipeline.voice import USD_PER_1K_CHARS, VOICE_MODEL
from app.worker import BUDGET_EXCEEDED, LEAD

SEED = 2026
SIGNUPS = (5, 6, 7, 8, 9, 10, 11, 13)
EMAIL_DOMAIN = "simulated.example"
LENGTHS = ((3, 0.25), (5, 0.55), (7, 0.20))
DAILY = 0.7
CURIOUS = 0.22
TOPICS = {
    "fc-barcelona-football": (0.85, 0.04),
    "fc-barcelona-basketball": (0.50, 0.06),
    "laliga": (0.65, 0.10),
    "champions-league": (0.70, 0.08),
    "euroleague": (0.50, 0.10),
    "liga-acb": (0.35, 0.18),
    "nba": (0.60, 0.24),
}
INTRO, CLOSING = 20.0, 18.0
AUDIO_PATH = "simulated/no-audio.mp3"

SELECT_CALLS = (("gpt-6-luna", 10_511, 646, 8_633), ("gpt-6-sol", 12_319, 1_617, 25_350))
WRITE_CALLS = (("gpt-6-sol", 9_392, 1_967, 29_732),)
JUDGE_CALL = ("gpt-6-luna", 12_494, 1_693, 17_317)
REWRITE_CALL = ("gpt-6-sol", 8_293, 1_075, 15_968)
REWRITE_SHARE = 0.35
FETCH_SECONDS, MASTER_SECONDS = 12.7, 9.5
VOICE_MS_PER_CHAR = 46

CHECK_FAILURE = (
    "check: the script failed twice (nba.3: unsupported: the source does not say he was the "
    "team's top scorer.)"
)
VOICE_FAILURE = "voice: a nba chunk was cut short twice"
CAP_FAILURE = f"{BUDGET_EXCEEDED}: $25.00 of $25.00 in the last 24 hours. Retry later."


@dataclass
class SimStage:
    stage: str
    status: str
    started_at: datetime
    finished_at: datetime
    error: str | None = None
    details: dict[str, Any] = field(default_factory=dict)
    calls: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class SimEpisode:
    row: dict[str, Any]
    stages: list[SimStage] = field(default_factory=list)
    events: list[tuple[str, float, datetime]] = field(default_factory=list)


@dataclass
class SimUser:
    email: str
    name: str
    created_at: datetime
    episodes: list[SimEpisode] = field(default_factory=list)


def week_start(now: datetime) -> datetime:
    monday = now.date() - timedelta(days=now.weekday())
    return datetime(monday.year, monday.month, monday.day, tzinfo=UTC)


def build(now: datetime, seed: int = SEED) -> list[SimUser]:
    rng = random.Random(seed)
    first_week = week_start(now) - timedelta(weeks=len(SIGNUPS) - 1)
    users: list[SimUser] = []
    for week, signups in enumerate(SIGNUPS):
        start = first_week + timedelta(weeks=week)
        span = min(timedelta(weeks=1), now - start).total_seconds()
        for _ in range(signups):
            number = len(users) + 1
            joined = start + timedelta(seconds=rng.uniform(0, span))
            user = SimUser(
                f"listener{number:03}@{EMAIL_DOMAIN}", f"Simulated listener {number}", joined
            )
            user.episodes = listener_episodes(rng, joined, now)
            users.append(user)
    return users


def listener_episodes(rng: random.Random, joined: datetime, now: datetime) -> list[SimEpisode]:
    length = rng.choices([m for m, _ in LENGTHS], [w for _, w in LENGTHS])[0]
    topics = [key for key, (follow, _) in TOPICS.items() if rng.random() < follow]
    if not topics:
        topics = ["fc-barcelona-football"]
    topics.sort(key=lambda key: (SPORTS.index(CATALOG[key].sport), list(CATALOG).index(key)))
    days = range(7) if rng.random() < DAILY else range(5)
    hour = timedelta(hours=5, minutes=30 * rng.randrange(6))
    affinity = rng.uniform(0, 0.1) if rng.random() < CURIOUS else rng.betavariate(2.4, 1.4)
    stops_after = rng.choice([1, 2, 3, 4]) if rng.random() < 0.3 else None
    episodes: list[SimEpisode] = []
    day = joined.date() + timedelta(days=1)
    while True:
        slot = datetime(day.year, day.month, day.day, tzinfo=UTC) + hour
        if slot > now:
            break
        weeks_in = (slot - joined).days // 7
        taste = affinity if stops_after is None or weeks_in < stops_after else 0.0
        if day.weekday() in days:
            first = not episodes
            episodes.append(
                episode(rng, "scheduled", slot, length, topics, taste, weeks_in, first, now)
            )
        if rng.random() < 0.05:
            manual = slot + timedelta(hours=rng.uniform(6, 14))
            if manual < now:
                episodes.append(
                    episode(rng, "manual", manual, length, topics, taste, weeks_in, False, now)
                )
        day += timedelta(days=1)
    return episodes


def episode(
    rng: random.Random,
    trigger: str,
    at: datetime,
    length: int,
    topics: list[str],
    affinity: float,
    weeks_in: int,
    first: bool,
    now: datetime,
) -> SimEpisode:
    scheduled = trigger == "scheduled"
    created = at - LEAD if scheduled else at
    started = created + timedelta(seconds=rng.uniform(1, 20))
    if scheduled and rng.random() < 0.02:
        started = at - timedelta(minutes=rng.uniform(0, 3))
    outcome = rng.random()
    row: dict[str, Any] = {
        "trigger": trigger,
        "scheduled_for": at,
        "created_at": created,
        "started_at": started,
        "attempts": 1,
        "title": "Simulated episode",
    }
    sim = SimEpisode(row)
    if outcome < 0.0075:
        row.update(status="failed", status_reason=CAP_FAILURE, attempts=0, finished_at=started)
        return sim
    clock = started
    clock = add_stage(sim, "fetch", clock, rng.lognormvariate(math.log(FETCH_SECONDS), 0.4))
    if outcome < 0.0375:
        reason = f"No fresh news for your interests since {at.date() - timedelta(days=1):%A}."
        end = clock + timedelta(seconds=rng.uniform(0.2, 1.0))
        sim.stages.append(SimStage("select", "completed", clock, end, None, {"skipped": reason}))
        row.update(status="skipped", status_reason=reason, finished_at=end)
        return sim
    clock = add_llm_stage(rng, sim, "select", clock, SELECT_CALLS)
    clock = add_llm_stage(rng, sim, "write", clock, WRITE_CALLS)
    rewrite = outcome < 0.0525 or rng.random() < REWRITE_SHARE
    judge = (JUDGE_CALL, REWRITE_CALL, JUDGE_CALL) if rewrite else (JUDGE_CALL,)
    if outcome < 0.0525:
        clock = add_llm_stage(rng, sim, "check", clock, judge, failed=CHECK_FAILURE)
        row.update(status="failed", status_reason=CHECK_FAILURE, finished_at=clock)
        return sim
    clock = add_llm_stage(rng, sim, "check", clock, judge)
    duration = round(length * 60 * rng.uniform(0.88, 1.02), 2)
    chapters = chapter_starts(rng, topics, duration)
    if outcome < 0.06:
        clock = add_voice_stage(rng, sim, clock, chapters, duration, failed=VOICE_FAILURE)
        row.update(status="failed", status_reason=VOICE_FAILURE, finished_at=clock)
        return sim
    clock = add_voice_stage(rng, sim, clock, chapters, duration)
    clock = add_stage(sim, "master", clock, rng.lognormvariate(math.log(MASTER_SECONDS), 0.15))
    row.update(
        status="completed",
        finished_at=clock,
        audio_path=AUDIO_PATH,
        duration_seconds=duration,
        chapters=chapters,
    )
    sim.events = listening(rng, clock, at, chapters, duration, affinity, weeks_in, first, now)
    return sim


def add_stage(sim: SimEpisode, stage: str, start: datetime, seconds: float) -> datetime:
    end = start + timedelta(seconds=seconds)
    sim.stages.append(SimStage(stage, "completed", start, end))
    return end


def add_llm_stage(
    rng: random.Random,
    sim: SimEpisode,
    stage: str,
    start: datetime,
    calls: tuple[tuple[str, int, int, int], ...],
    details: dict[str, Any] | None = None,
    failed: str | None = None,
) -> datetime:
    clock = start
    rows = []
    for model, tokens_in, tokens_out, latency in calls:
        tokens_in, tokens_out = jitter(rng, tokens_in), jitter(rng, tokens_out)
        _, _, price_write, price_out = PRICES[model]
        clock += timedelta(milliseconds=jitter(rng, latency))
        rows.append(
            {
                "provider": "openai",
                "model": model,
                "input_tokens": tokens_in,
                "output_tokens": tokens_out,
                "cost_usd": round((tokens_in * price_write + tokens_out * price_out) / 1e6, 6),
                "latency_ms": jitter(rng, latency),
                "created_at": clock,
            }
        )
    status = "failed" if failed else "completed"
    sim.stages.append(SimStage(stage, status, start, clock, failed, details or {}, rows))
    return clock


def add_voice_stage(
    rng: random.Random,
    sim: SimEpisode,
    start: datetime,
    chapters: list[dict[str, Any]],
    duration: float,
    failed: str | None = None,
) -> datetime:
    clock = start
    rows = []
    ends = [chapter["start"] for chapter in chapters[1:]] + [duration]
    for chapter, end in zip(chapters, ends, strict=True):
        chars = round((end - chapter["start"]) * CHARS_PER_SECOND)
        latency = jitter(rng, chars * VOICE_MS_PER_CHAR)
        clock += timedelta(milliseconds=latency)
        rows.append(
            {
                "provider": "elevenlabs",
                "model": VOICE_MODEL,
                "characters": chars,
                "cost_usd": round(chars * USD_PER_1K_CHARS / 1000, 6),
                "latency_ms": latency,
                "created_at": clock,
            }
        )
    billed = sum(row["characters"] for row in rows)
    details = {"voice": VOICE_MODEL, "billed_characters": billed, "reused_characters": 0}
    status = "failed" if failed else "completed"
    sim.stages.append(SimStage("voice", status, start, clock, failed, details, rows))
    return clock


def jitter(rng: random.Random, value: float) -> int:
    return max(1, round(value * rng.uniform(0.75, 1.25)))


def chapter_starts(rng: random.Random, topics: list[str], duration: float) -> list[dict[str, Any]]:
    weights = [rng.uniform(0.7, 1.5) for _ in topics]
    body = duration - 0.5 - INTRO - CLOSING
    chapters = [{"key": "intro", "start": 0.5}]
    start = 0.5 + INTRO
    for topic, weight in zip(topics, weights, strict=True):
        chapters.append({"key": topic, "start": round(start, 2)})
        start += body * weight / sum(weights)
    chapters.append({"key": "closing", "start": round(start, 2)})
    return chapters


def listening(
    rng: random.Random,
    ready: datetime,
    at: datetime,
    chapters: list[dict[str, Any]],
    duration: float,
    affinity: float,
    weeks_in: int,
    first: bool,
    now: datetime,
) -> list[tuple[str, float, datetime]]:
    chance = min(0.95, affinity + 0.2) if first else affinity * 0.93**weeks_in
    if rng.random() >= chance:
        return []
    played = max(ready, at) + timedelta(hours=min(30.0, rng.expovariate(1 / 1.5)))
    if played > now:
        return []
    fate = rng.random()
    stop = rng.uniform(20, 120) if fate < 0.22 else duration if fate < 0.62 else None
    if stop is None:
        stop = rng.uniform(120, duration)
    ends = [chapter["start"] for chapter in chapters[1:]] + [duration]
    skipped = [
        (chapter["start"], end)
        for chapter, end in zip(chapters, ends, strict=True)
        if chapter["key"] in TOPICS and rng.random() < TOPICS[chapter["key"]][1]
    ]
    events: list[tuple[str, float, datetime]] = [("play", 0.0, played)]
    heard = 0.0
    for slot in range(math.ceil(duration / 15)):
        start, end = slot * 15.0, min(slot * 15.0 + 15, duration)
        if end > stop + 0.5 or any(start < b and a < end for a, b in skipped):
            continue
        heard += end - start
        events.append(("heartbeat", start, played + timedelta(seconds=heard)))
    if len(events) > 1 and rng.random() < 0.04:
        again = played + timedelta(days=1)
        if again < now:
            events += [("play", 0.0, again), ("heartbeat", 0.0, again + timedelta(seconds=15))]
    return events


def seed_synthetic(session: Session, now: datetime) -> int:
    users = build(now)
    user_ids = session.scalars(
        insert(User).returning(User.id, sort_by_parameter_order=True),
        [
            {"email": u.email, "name": u.name, "created_at": u.created_at, "is_synthetic": True}
            for u in users
        ],
    ).all()
    episodes = [(uid, ep) for uid, u in zip(user_ids, users, strict=True) for ep in u.episodes]
    episode_ids = session.scalars(
        insert(Episode).returning(Episode.id, sort_by_parameter_order=True),
        [{"user_id": uid, **ep.row} for uid, ep in episodes],
    ).all()
    stages = [
        (eid, st) for eid, (_, ep) in zip(episode_ids, episodes, strict=True) for st in ep.stages
    ]
    stage_ids = session.scalars(
        insert(StageRun).returning(StageRun.id, sort_by_parameter_order=True),
        [
            {
                "episode_id": eid,
                "attempt": 1,
                "stage": st.stage,
                "status": st.status,
                "started_at": st.started_at,
                "finished_at": st.finished_at,
                "error": st.error,
                "details": st.details,
            }
            for eid, st in stages
        ],
    ).all()
    calls = [
        {"stage_run_id": sid, **call}
        for sid, (_, st) in zip(stage_ids, stages, strict=True)
        for call in st.calls
    ]
    if calls:
        session.execute(insert(ProviderCall), calls)
    events = [
        {"episode_id": eid, "kind": kind, "position_seconds": position, "created_at": created}
        for eid, (_, ep) in zip(episode_ids, episodes, strict=True)
        for kind, position, created in ep.events
    ]
    if events:
        session.execute(insert(ListenEvent), events)
    return len(user_ids)


def has_synthetic(session: Session) -> bool:
    return session.scalar(select(User.id).where(User.is_synthetic).limit(1)) is not None


def seed_if_missing(session: Session, now: datetime) -> int:
    return 0 if has_synthetic(session) else seed_synthetic(session, now)


def delete_synthetic(session: Session) -> None:
    session.execute(delete(User).where(User.is_synthetic))


def main() -> None:
    parser = argparse.ArgumentParser(description="Create the dashboard's simulated listeners.")
    parser.add_argument("--reset", action="store_true", help="delete and recreate them as of now")
    args = parser.parse_args()
    with Session(engine) as session:
        if args.reset:
            delete_synthetic(session)
        count = seed_if_missing(session, datetime.now(UTC))
        session.commit()
    print(f"Created {count} simulated listeners" if count else "They already exist: use --reset")


if __name__ == "__main__":
    main()
