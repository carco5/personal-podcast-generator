"""The worker: schedules episodes, generates queued ones and ingests the catalogue."""

import logging
import signal
import sys
import time
from collections.abc import Callable
from contextlib import AbstractContextManager, closing
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import FrameType

from sqlalchemy import exists, func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import engine
from app.models import Episode, Interest, PodcastSettings, ProviderCall, StageRun, User
from app.pipeline.llm import Llm, OpenAILlm
from app.pipeline.runner import finish, run_episode
from app.pipeline.voice import ElevenLabsVoice, ToneVoice, Voice
from app.schedule import latest_slot
from app.sources.http import Fetcher
from app.sources.ingest import ingest
from app.sources.registry import catalogue_sources

log = logging.getLogger("app.worker")

INGEST_EVERY = timedelta(hours=3)
LEAD = timedelta(minutes=30)
CATCH_UP = timedelta(hours=12)
STALE_AFTER = timedelta(minutes=30)
BUDGET_WINDOW = timedelta(hours=24)

INTERRUPTED = "Interrupted: the worker stopped while generating. Retry to resume where it stopped."
BUDGET_EXCEEDED = "Daily spending cap reached"

REAL_USERS = select(User.id).where(User.is_synthetic.is_(False))


def recover_stale(session: Session, now: datetime) -> list[int]:
    ids = session.scalars(
        update(Episode)
        .where(Episode.status == "in_progress", Episode.started_at < now - STALE_AFTER)
        .values(status="failed", status_reason=INTERRUPTED, finished_at=now)
        .returning(Episode.id)
    ).all()
    if ids:
        session.execute(
            update(StageRun)
            .where(StageRun.episode_id.in_(ids), StageRun.status == "in_progress")
            .values(status="failed", error="interrupted", finished_at=now)
        )
    session.commit()
    return list(ids)


def schedule_due(session: Session, now: datetime) -> int:
    has_interests = exists().where(Interest.user_id == PodcastSettings.user_id)
    created = 0
    listeners = select(PodcastSettings).where(
        has_interests, PodcastSettings.user_id.in_(REAL_USERS)
    )
    for podcast in session.scalars(listeners):
        slot = latest_slot(podcast, now + LEAD)
        if slot is None or slot < now - CATCH_UP or slot < podcast.updated_at:
            continue
        taken = select(Episode.id).where(
            Episode.user_id == podcast.user_id,
            (Episode.scheduled_for == slot) | Episode.status.in_(("queued", "in_progress")),
        )
        if session.scalar(taken.limit(1)) is not None:
            continue
        statement = insert(Episode).values(
            user_id=podcast.user_id, trigger="scheduled", scheduled_for=slot
        )
        inserted = statement.on_conflict_do_nothing().returning(Episode.id)
        created += len(session.scalars(inserted).all())
    session.commit()
    return created


def spent_in_window(session: Session, now: datetime) -> Decimal:
    return session.scalar(
        select(func.coalesce(func.sum(ProviderCall.cost_usd), 0))
        .join(StageRun, StageRun.id == ProviderCall.stage_run_id)
        .join(Episode, Episode.id == StageRun.episode_id)
        .where(ProviderCall.created_at > now - BUDGET_WINDOW, Episode.user_id.in_(REAL_USERS))
    )


def claim_next(session: Session) -> Episode | None:
    return session.scalar(
        select(Episode)
        .where(Episode.status == "queued", Episode.user_id.in_(REAL_USERS))
        .order_by(Episode.scheduled_for, Episode.id)
        .limit(1)
        .with_for_update(skip_locked=True)
    )


def process_next(
    session: Session, config: Settings, *, llm: Llm, voice: Voice, now: datetime
) -> Episode | None:
    episode = claim_next(session)
    if episode is None:
        session.rollback()
        return None
    spent, cap = spent_in_window(session, now), config.worker_daily_budget_usd
    if spent >= cap:
        reason = f"{BUDGET_EXCEEDED}: ${spent:.2f} of ${cap:.2f} in the last 24 hours."
        finish(session, episode, "failed", f"{reason} Retry later.")
        return episode
    with closing(Fetcher()) as fetcher:
        return run_episode(session, episode, llm=llm, voice=voice, fetcher=fetcher, config=config)


def tick(
    session: Session, config: Settings, *, llm: Llm, voice: Voice, now: datetime
) -> Episode | None:
    if recovered := recover_stale(session, now):
        log.warning("Recovered interrupted episodes %s", recovered)
    if scheduled := schedule_due(session, now):
        log.info("Scheduled %s episode(s)", scheduled)
    episode = process_next(session, config, llm=llm, voice=voice, now=now)
    if episode is not None:
        log.info(
            "Episode %s (%s, user %s): %s %s",
            episode.id,
            episode.trigger,
            episode.user_id,
            episode.status,
            episode.status_reason or "",
        )
    return episode


def ingest_catalogue(session: Session, config: Settings) -> None:
    with closing(Fetcher()) as fetcher:
        report = ingest(session, catalogue_sources(config).values(), fetcher)
    saved = sum(result.get("saved", 0) for result in report.values())
    failed = [key for key, result in report.items() if "error" in result]
    log.info("Ingested the catalogue: %s new or updated, failed: %s", saved, failed or "none")


class Shutdown:
    """Set by SIGTERM: the worker finishes what it is doing, then exits."""

    def __init__(self) -> None:
        self.requested = False

    def request(self, signum: int, frame: FrameType | None) -> None:
        self.requested = True

    def sleep(self, seconds: float) -> None:
        deadline = time.monotonic() + seconds
        while not self.requested and (left := deadline - time.monotonic()) > 0:
            time.sleep(min(1.0, left))


def run_forever(
    config: Settings,
    *,
    llm: Llm,
    voice: Voice,
    shutdown: Shutdown,
    session_factory: Callable[[], AbstractContextManager[Session]] = lambda: Session(engine),
) -> None:
    last_ingest: datetime | None = None
    while not shutdown.requested:
        now = datetime.now(UTC)
        episode = None
        with session_factory() as session:
            try:
                episode = tick(session, config, llm=llm, voice=voice, now=now)
                due = last_ingest is None or now - last_ingest >= INGEST_EVERY
                if due and not shutdown.requested:
                    ingest_catalogue(session, config)
                    last_ingest = now
            except Exception:
                session.rollback()
                log.exception("Worker iteration failed; retrying on the next one")
        if episode is None:
            shutdown.sleep(config.worker_poll_seconds)
    log.info("Worker stopped")


def main() -> None:
    logging.basicConfig(
        level=logging.WARNING, format="%(asctime)s %(levelname)s [%(name)s] %(message)s"
    )
    logging.getLogger("app").setLevel(logging.INFO)
    config = get_settings()
    if missing := config.missing_generation_keys():
        sys.exit(
            f"The worker needs {' and '.join(missing)} to generate episodes (see .env.example)"
        )
    llm = OpenAILlm(config.openai_api_key)
    if config.worker_voice == "elevenlabs":
        voice: Voice = ElevenLabsVoice(config.elevenlabs_api_key)
    else:
        voice = ToneVoice()
    shutdown = Shutdown()
    signal.signal(signal.SIGTERM, shutdown.request)
    log.info(
        "Worker started: voice %s, daily cap $%s, polling every %s s",
        config.worker_voice,
        config.worker_daily_budget_usd,
        config.worker_poll_seconds,
    )
    run_forever(config, llm=llm, voice=voice, shutdown=shutdown)


if __name__ == "__main__":
    main()
