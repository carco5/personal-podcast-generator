import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.config import Settings
from app.models import Article, Episode, EpisodeArticle, ProviderCall, StageRun
from app.pipeline import fetch, master, runner
from app.pipeline.checks import Judgement
from app.pipeline.common import Run
from app.pipeline.editorial import EditorialPlan
from app.pipeline.repair import Repairs
from app.pipeline.runner import run_episode
from app.pipeline.script import Script
from app.pipeline.selection import Picks
from app.pipeline.voice import ToneVoice
from app.sources.http import Fetcher
from tests.fakes import FakeLlm, approve_all, make_article, make_listener

pytestmark = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg is not installed")


@pytest.fixture(autouse=True)
def no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(fetch, "episode_sources", lambda run: {})


def setup(session: Session, with_news: bool = True) -> Episode:
    user, _, _ = make_listener(session, [("euroleague", "high")], length_minutes=3)
    if with_news:
        recent = datetime.now(UTC) - timedelta(hours=2)
        meta = {"competition": "euroleague", "type": "result", "round": 1, "teams": ["A", "B"]}
        make_article(session, "euroleague-api", "A beat B", recent, meta=meta)
        make_article(session, "eurohoops-euroleague", "Big signing", recent)
    episode = Episode(user_id=user.id, trigger="manual", scheduled_for=datetime.now(UTC))
    session.add(episode)
    session.flush()
    return episode


def generate(session: Session, episode: Episode, llm: FakeLlm, data_dir: Path) -> Episode:
    config = Settings(_env_file=None, openai_api_key=None, data_dir=data_dir)
    return run_episode(
        session, episode, llm=llm, voice=ToneVoice(), fetcher=Fetcher(), config=config
    )


def stages(session: Session, episode: Episode) -> list[tuple[int, str, str]]:
    rows = session.scalars(
        select(StageRun).where(StageRun.episode_id == episode.id).order_by(StageRun.id)
    )
    return [(row.attempt, row.stage, row.status) for row in rows]


def test_a_full_episode(session: Session, tmp_path: Path) -> None:
    episode = generate(session, setup(session), FakeLlm(), tmp_path)

    assert episode.status == "completed" and episode.status_reason is None
    assert (tmp_path / episode.audio_path).exists() and episode.duration_seconds > 5
    assert [chapter["key"] for chapter in episode.chapters] == ["intro", "euroleague", "closing"]
    assert [stage for _, stage, _ in stages(session, episode)] == [
        "fetch",
        "select",
        "write",
        "check",
        "voice",
        "master",
    ]
    assert {status for _, _, status in stages(session, episode)} == {"completed"}
    calls = session.execute(
        select(StageRun.stage, ProviderCall.provider)
        .join(ProviderCall, ProviderCall.stage_run_id == StageRun.id)
        .where(StageRun.episode_id == episode.id)
    ).all()
    assert {(stage, provider) for stage, provider in calls} == {
        ("select", "openai"),
        ("write", "openai"),
        ("check", "openai"),
        ("voice", "elevenlabs"),
    }


def test_as_of_reproduces_a_past_moment(session: Session, tmp_path: Path) -> None:
    episode = setup(session)
    as_of = datetime.now(UTC) - timedelta(hours=1)
    later = datetime.now(UTC) - timedelta(minutes=10)
    make_article(session, "eurohoops-euroleague", "Later news", later)
    config = Settings(_env_file=None, openai_api_key=None, data_dir=tmp_path)

    run_episode(
        session,
        episode,
        llm=FakeLlm(),
        voice=ToneVoice(),
        fetcher=Fetcher(),
        config=config,
        as_of=as_of,
    )

    assert stages(session, episode)[0][1] == "select"
    assert episode.plan["selected_at"] == as_of.isoformat()
    titles = session.scalars(
        select(Article.title)
        .join(EpisodeArticle, EpisodeArticle.article_id == Article.id)
        .where(EpisodeArticle.episode_id == episode.id)
    ).all()
    assert "Big signing" in titles and "Later news" not in titles
    master_details = session.scalars(
        select(StageRun.details).where(
            StageRun.episode_id == episode.id, StageRun.stage == "master"
        )
    ).one()
    metrics = master_details["metrics"]
    assert metrics["llm_calls"] == 6 and metrics["voice_calls"] > 0
    assert metrics["planned_chars"] == 2232 and metrics["chars_per_second"] == pytest.approx(
        12.4, abs=0.3
    )


def test_a_retry_resumes_without_paying_again(
    session: Session, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    llm = FakeLlm()
    episode = setup(session)
    with monkeypatch.context() as patch:
        patch.setattr(master.audio, "loudness", lambda path: (-25.0, -9.0))
        generate(session, episode, llm, tmp_path)
    assert episode.status == "failed" and "loudness -25.0 LUFS" in episode.status_reason
    paid_before = len(llm.prompts)

    episode.status, episode.status_reason = "queued", None
    generate(session, episode, llm, tmp_path)

    assert episode.status == "completed" and episode.attempts == 2
    assert len(llm.prompts) == paid_before
    second = [stage for attempt, stage, _ in stages(session, episode) if attempt == 2]
    assert second == ["fetch", "voice", "master"]
    voice_run = session.scalars(
        select(StageRun).where(StageRun.stage == "voice", StageRun.attempt == 2)
    ).one()
    assert voice_run.details["generated_characters"] == 0


def test_recheck_repairs_turns_without_rewriting(session: Session, tmp_path: Path) -> None:
    episode = generate(session, setup(session), FakeLlm(), tmp_path)
    flags = iter([{"intro.1": "overstated"}, {}])
    llm = FakeLlm({Judgement: lambda prompt: approve_all(prompt, next(flags))})
    config = Settings(_env_file=None, openai_api_key=None, data_dir=tmp_path)

    run_episode(
        session, episode, llm=llm, voice=ToneVoice(), fetcher=Fetcher(), config=config, recheck=True
    )

    assert episode.status == "completed" and episode.attempts == 2
    second = [stage for attempt, stage, _ in stages(session, episode) if attempt == 2]
    assert second == ["check", "voice", "master"]
    assert [schema for schema, _ in llm.prompts] == [Judgement, Repairs, Judgement]
    check = session.scalars(
        select(StageRun.details).where(
            StageRun.episode_id == episode.id, StageRun.stage == "check", StageRun.attempt == 2
        )
    ).one()
    assert check["recheck"] is True and check["repaired"] == ["intro.1"] and not check["removed"]
    assert any("Expand the lead story" in warning for warning in check["warnings"])
    assert Script.model_validate(episode.script).segments[0].turns[0].text == (
        "That's the one to watch."
    )


def test_nothing_new_ends_as_skipped(session: Session, tmp_path: Path) -> None:
    episode = generate(session, setup(session, with_news=False), FakeLlm(), tmp_path)

    assert episode.status == "skipped"
    assert episode.status_reason.startswith("No fresh news for your interests")
    assert stages(session, episode) == [(1, "fetch", "completed"), (1, "select", "completed")]
    assert episode.audio_path is None


def test_a_database_error_fails_the_episode_cleanly(
    session: Session, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def broken_stage(run: Run) -> dict:
        run.session.execute(text("SELECT 1 / 0"))
        return {}

    monkeypatch.setattr(runner, "STAGES", [("fetch", broken_stage, lambda run: True)])
    episode = generate(session, setup(session), FakeLlm(), tmp_path)

    assert episode.status == "failed"
    assert episode.status_reason.startswith("fetch: DataError: (psycopg.errors.DivisionByZero)")
    assert "SELECT" not in episode.status_reason
    assert stages(session, episode) == [(1, "fetch", "failed")]


def test_an_unexpected_error_fails_the_episode_cleanly(session: Session, tmp_path: Path) -> None:
    def broken_writer(prompt: str) -> Script:
        raise RuntimeError("model unavailable")

    episode = generate(session, setup(session), FakeLlm({Script: broken_writer}), tmp_path)

    assert episode.status == "failed"
    assert episode.status_reason == "write: RuntimeError: model unavailable"
    assert stages(session, episode)[-1] == (1, "write", "failed")
    assert session.scalars(select(ProviderCall)).all()


def test_an_interrupted_check_is_checked_again(session: Session, tmp_path: Path) -> None:
    def interrupted_judge(prompt: str) -> Judgement:
        raise KeyboardInterrupt

    episode = setup(session)
    with pytest.raises(KeyboardInterrupt):
        generate(session, episode, FakeLlm({Judgement: interrupted_judge}), tmp_path)
    assert stages(session, episode)[-1] == (1, "check", "failed")
    check = session.scalars(select(StageRun).where(StageRun.stage == "check")).one()
    assert check.error == "interrupted"

    llm = FakeLlm()
    episode.status = "queued"
    generate(session, episode, llm, tmp_path)

    assert episode.status == "completed" and episode.attempts == 2
    second = [stage for attempt, stage, _ in stages(session, episode) if attempt == 2]
    assert second == ["fetch", "check", "voice", "master"]
    schemas = [schema for schema, _ in llm.prompts]
    assert schemas[0] is Judgement and Picks not in schemas and EditorialPlan not in schemas
