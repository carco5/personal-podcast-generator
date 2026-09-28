from datetime import UTC, datetime, time, timedelta

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import (
    Article,
    Episode,
    EpisodeArticle,
    Interest,
    PodcastSettings,
    ProviderCall,
    StageRun,
    User,
)


def make_user(session: Session, email: str = "listener@example.com") -> User:
    user = User(email=email, name="Listener")
    session.add(user)
    session.flush()
    return user


def make_article(session: Session, url: str = "https://example.com/a") -> Article:
    article = Article(
        source="eurohoops-euroleague",
        kind="article",
        official=False,
        language="en",
        url=url,
        title="Title",
        body="Body",
        published_at=datetime.now(UTC),
    )
    session.add(article)
    session.flush()
    return article


@pytest.mark.parametrize(
    ("row", "field", "bad_value", "constraint"),
    [
        ("episode", "status", "done", "ck_episodes_status"),
        ("episode", "trigger", "api", "ck_episodes_trigger"),
        ("episode", "status", "completed", "ck_episodes_audio"),
        ("episode", "audio_path", "episodes/1.mp3", "ck_episodes_audio"),
        ("episode", "status", "skipped", "ck_episodes_reason"),
        ("episode", "status_reason", "No fresh news", "ck_episodes_reason"),
        ("settings", "length_minutes", 4, "ck_podcast_settings_length_minutes"),
        ("settings", "tone", "funny", "ck_podcast_settings_tone"),
        ("interest", "weight", "huge", "ck_interests_weight"),
        ("interest", "keywords", ["euroleague"], "ck_interests_keywords"),
        ("article", "kind", "video", "ck_articles_kind"),
        ("article", "language", "fr", "ck_articles_language"),
        ("stage_run", "stage", "publish", "ck_stage_runs_stage"),
        ("stage_run", "status", "done", "ck_stage_runs_status"),
        ("provider_call", "provider", "google", "ck_provider_calls_provider"),
        ("provider_call", "characters", 120, "ck_provider_calls_usage"),
    ],
)
def test_check_constraints_reject_bad_values(
    session: Session, row: str, field: str, bad_value: object, constraint: str
) -> None:
    user = make_user(session)
    episode = Episode(user_id=user.id, trigger="manual", scheduled_for=func.now())
    session.add(episode)
    session.flush()
    stage_run = StageRun(episode_id=episode.id, attempt=1, stage="write", status="completed")
    session.add(stage_run)
    session.flush()
    rows = {
        "episode": Episode(
            user_id=user.id, trigger="manual", scheduled_for=datetime.now(UTC) + timedelta(1)
        ),
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
        "article": Article(
            source="euroleague-api",
            kind="data",
            official=True,
            language="en",
            url="https://example.com/data",
            title="Result",
            body="Body",
            published_at=datetime.now(UTC),
        ),
        "stage_run": StageRun(episode_id=episode.id, attempt=1, stage="voice", status="failed"),
        "provider_call": ProviderCall(
            stage_run_id=stage_run.id,
            provider="openai",
            model="gpt-6-sol",
            input_tokens=1000,
            output_tokens=300,
            cost_usd=0.005,
            latency_ms=7000,
        ),
    }
    setattr(rows[row], field, bad_value)
    episode.status, episode.audio_path = "completed", "episodes/0.mp3"
    session.add(rows[row])
    with pytest.raises(IntegrityError, match=constraint):
        session.flush()


def test_one_episode_in_flight_per_user(session: Session) -> None:
    user = make_user(session)
    now = datetime.now(UTC)
    session.add(
        Episode(
            user_id=user.id,
            trigger="manual",
            scheduled_for=now,
            status="completed",
            audio_path="episodes/1.mp3",
        )
    )
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


def test_article_url_is_unique(session: Session) -> None:
    make_article(session)

    with pytest.raises(IntegrityError, match="uq_articles_url"):
        make_article(session)


def test_deleting_an_episode_deletes_its_pipeline_rows(session: Session) -> None:
    user = make_user(session)
    article = make_article(session)
    episode = Episode(user_id=user.id, trigger="manual", scheduled_for=func.now())
    session.add(episode)
    session.flush()
    stage_run = StageRun(episode_id=episode.id, attempt=1, stage="voice", status="completed")
    session.add_all(
        [
            EpisodeArticle(
                episode_id=episode.id, article_id=article.id, source_id="S1", block="nba", rank=1
            ),
            stage_run,
        ]
    )
    session.flush()
    session.add(
        ProviderCall(
            stage_run_id=stage_run.id,
            provider="elevenlabs",
            model="eleven_v3",
            characters=663,
            cost_usd=0.0663,
            latency_ms=6400,
        )
    )
    session.flush()

    session.delete(episode)
    session.flush()

    assert session.scalars(select(EpisodeArticle)).all() == []
    assert session.scalars(select(StageRun)).all() == []
    assert session.scalars(select(ProviderCall)).all() == []
    assert session.scalars(select(Article)).all() == [article]


def test_an_article_in_use_cannot_be_deleted(session: Session) -> None:
    user = make_user(session)
    article = make_article(session)
    episode = Episode(user_id=user.id, trigger="manual", scheduled_for=func.now())
    session.add(episode)
    session.flush()
    session.add(
        EpisodeArticle(
            episode_id=episode.id, article_id=article.id, source_id="S1", block="nba", rank=1
        )
    )
    session.flush()

    session.delete(article)
    with pytest.raises(IntegrityError, match="fk_episode_articles_article_id_articles"):
        session.flush()
