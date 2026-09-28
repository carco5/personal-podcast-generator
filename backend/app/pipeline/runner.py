import argparse
import logging
import sys
from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import engine
from app.demo import ensure_demo_user
from app.models import Episode, Interest, PodcastSettings, ProviderCall, Stage, StageRun
from app.pipeline.checks import check_script
from app.pipeline.common import EpisodeSkipped, Run, StageFailed
from app.pipeline.fetch import fetch
from app.pipeline.llm import Llm, OpenAILlm
from app.pipeline.master import master_episode
from app.pipeline.script import write_script
from app.pipeline.selection import select_stories
from app.pipeline.voice import ElevenLabsVoice, ToneVoice, Voice, voice_script
from app.sources.http import Fetcher
from app.sources.ingest import short_error

log = logging.getLogger(__name__)


def passed_check(run: Run) -> bool:
    last = run.session.scalar(
        select(StageRun.status)
        .where(StageRun.episode_id == run.episode.id, StageRun.stage == "check")
        .order_by(StageRun.id.desc())
        .limit(1)
    )
    return last == "completed"


STAGES: list[tuple[Stage, Callable[[Run], dict], Callable[[Run], bool]]] = [
    ("fetch", fetch, lambda run: True),
    ("select", select_stories, lambda run: run.episode.plan is None),
    ("write", write_script, lambda run: run.episode.script is None),
    ("check", check_script, lambda run: not passed_check(run)),
    ("voice", voice_script, lambda run: True),
    ("master", master_episode, lambda run: True),
]


def run_episode(
    session: Session,
    episode: Episode,
    *,
    llm: Llm,
    voice: Voice,
    fetcher: Fetcher,
    config: Settings,
) -> Episode:
    now = datetime.now(UTC)
    episode.status, episode.status_reason = "in_progress", None
    episode.attempts += 1
    episode.started_at, episode.finished_at = now, None
    session.commit()
    interests = session.scalars(
        select(Interest).where(Interest.user_id == episode.user_id).order_by(Interest.id)
    ).all()
    run = Run(
        session=session,
        episode=episode,
        podcast=session.get_one(PodcastSettings, episode.user_id),
        interests=list(interests),
        config=config,
        llm=llm,
        voice=voice,
        fetcher=fetcher,
        now=now,
    )
    try:
        result: dict = {}
        for name, function, pending in STAGES:
            if pending(run):
                result = run_stage(run, name, function)
        finish(session, episode, "completed", None, result)
    except EpisodeSkipped as skipped:
        finish(session, episode, "skipped", str(skipped))
    except StageFailed as failed:
        finish(session, episode, "failed", str(failed))
    return episode


def run_stage(run: Run, name: Stage, function: Callable[[Run], dict]) -> dict:
    session = run.session
    episode_id = run.episode.id
    stage = StageRun(
        episode_id=episode_id, attempt=run.episode.attempts, stage=name, status="in_progress"
    )
    session.add(stage)
    session.commit()
    run.calls = []
    status, error, details = "completed", None, {}
    try:
        details = function(run)
        return details
    except EpisodeSkipped as skipped:
        details = {"skipped": str(skipped)}
        raise
    except StageFailed as failed:
        status, error, details = "failed", str(failed), failed.details
        raise
    except Exception as unexpected:
        session.rollback()
        log.exception("Stage %s of episode %s failed", name, episode_id)
        status, error = "failed", short_error(unexpected)
        raise StageFailed(f"{name}: {error}") from unexpected
    finally:
        stage.status, stage.error, stage.details = status, error, details
        stage.finished_at = datetime.now(UTC)
        session.add_all(
            ProviderCall(
                stage_run_id=stage.id,
                provider=call.provider,
                model=call.model,
                input_tokens=call.input_tokens,
                output_tokens=call.output_tokens,
                characters=call.characters,
                cost_usd=Decimal(f"{call.cost_usd:.6f}"),
                latency_ms=call.latency_ms,
            )
            for call in run.calls
        )
        session.commit()


def finish(
    session: Session, episode: Episode, status: str, reason: str | None, result: dict | None = None
) -> None:
    episode.status, episode.status_reason = status, reason
    episode.finished_at = datetime.now(UTC)
    if result:
        episode.audio_path = result["audio_path"]
        episode.duration_seconds = result["duration_seconds"]
        episode.chapters = result["chapters"]
    session.commit()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate one episode. It spends OpenAI credits, and ElevenLabs credits "
        "unless --tone-voice is given."
    )
    parser.add_argument("episode_id", nargs="?", type=int, help="an existing episode")
    parser.add_argument(
        "--new", action="store_true", help="create a manual episode for the demo user"
    )
    parser.add_argument("--tone-voice", action="store_true", help="use the free development voice")
    args = parser.parse_args()
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")
    config = get_settings()
    if config.openai_api_key is None:
        sys.exit("OPENAI_API_KEY is not set")
    if not args.tone_voice and config.elevenlabs_api_key is None:
        sys.exit("ELEVENLABS_API_KEY is not set (or use --tone-voice)")
    voice = ToneVoice() if args.tone_voice else ElevenLabsVoice(config.elevenlabs_api_key)
    with Session(engine) as session:
        if args.new:
            user = ensure_demo_user(session)
            episode = Episode(user_id=user.id, trigger="manual", scheduled_for=datetime.now(UTC))
            session.add(episode)
            session.commit()
        elif args.episode_id is None or (episode := session.get(Episode, args.episode_id)) is None:
            sys.exit("Give an existing episode id, or --new")
        run_episode(
            session,
            episode,
            llm=OpenAILlm(config.openai_api_key),
            voice=voice,
            fetcher=Fetcher(),
            config=config,
        )
        print(f"Episode {episode.id}: {episode.status} {episode.status_reason or ''}")
        stages = session.scalars(
            select(StageRun).where(StageRun.episode_id == episode.id).order_by(StageRun.id)
        )
        for stage in stages:
            cost = sum(call.cost_usd for call in stage_calls(session, stage))
            print(
                f"  {stage.attempt} {stage.stage:>6}: {stage.status} ${cost:.4f} {stage.error or ''}"
            )
        if episode.audio_path:
            print(f"Audio: {config.data_dir / episode.audio_path} ({episode.duration_seconds} s)")


def stage_calls(session: Session, stage: StageRun) -> list[ProviderCall]:
    return list(session.scalars(select(ProviderCall).where(ProviderCall.stage_run_id == stage.id)))


if __name__ == "__main__":
    main()
