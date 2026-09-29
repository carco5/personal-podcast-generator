import json
import shutil
from datetime import datetime, time
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import ROOT
from app.models import Article, Episode, EpisodeArticle, Interest, PodcastSettings, User

DEMO_USER_EMAIL = "demo@example.com"

DEFAULT_SETTINGS = {
    "show_name": "Barça & Beyond",
    "length_minutes": 5,
    "tone": "casual",
    "hosts": [
        {
            "role": "host",
            "name": "George",
            "personality": "Warm, energetic presenter who drives the episode and gives the facts.",
        },
        {
            "role": "analyst",
            "name": "Sarah",
            "personality": "Sharp, curious analyst who adds context, opinions and questions.",
        },
    ],
    "schedule_days": [1, 2, 3, 4, 5, 6, 7],
    "schedule_time": time(7, 0),
    "timezone": "Europe/Madrid",
}

DEMO_INTERESTS = [
    ("fc-barcelona-football", "high"),
    ("fc-barcelona-basketball", "high"),
    ("laliga", "medium"),
    ("champions-league", "medium"),
    ("liga-acb", "medium"),
    ("euroleague", "medium"),
    ("nba", "low"),
]

SAMPLE_EPISODE = Path(__file__).resolve().parent / "sample_episode.json"
SAMPLE_AUDIO = ROOT / "sample.mp3"
SAMPLE_AUDIO_PATH = "demo/sample.mp3"


def ensure_demo_user(session: Session) -> User:
    """Return the demo user, creating it with default settings if it does not exist."""
    user = session.scalar(select(User).where(User.email == DEMO_USER_EMAIL))
    if user is None:
        user = User(email=DEMO_USER_EMAIL, name="Demo listener")
        session.add(user)
        session.flush()
        session.add(PodcastSettings(user_id=user.id, **DEFAULT_SETTINGS))
    return user


def seed_demo_listener(session: Session, data_dir: Path) -> User:
    """Return the demo user; on a fresh database, create it with the sample's podcast."""
    existing = session.scalar(select(User).where(User.email == DEMO_USER_EMAIL))
    if existing is not None:
        return existing
    user = ensure_demo_user(session)
    for topic, weight in DEMO_INTERESTS:
        session.add(Interest(user_id=user.id, kind="catalog", topic=topic, weight=weight))
    add_sample_episode(session, user, data_dir)
    return user


def add_sample_episode(session: Session, user: User, data_dir: Path) -> Episode:
    data = json.loads(SAMPLE_EPISODE.read_text(encoding="utf-8"))
    fields = data["episode"]
    times = ("scheduled_for", "created_at", "started_at", "finished_at")
    episode = Episode(
        user_id=user.id,
        status="completed",
        audio_path=SAMPLE_AUDIO_PATH,
        **{name: datetime.fromisoformat(fields[name]) for name in times},
        **{name: value for name, value in fields.items() if name not in times},
    )
    session.add(episode)
    session.flush()
    for source in data["sources"]:
        info = source["article"]
        article = session.scalar(select(Article).where(Article.url == info["url"]))
        if article is None:
            published = datetime.fromisoformat(info["published_at"])
            article = Article(**{**info, "published_at": published})
            session.add(article)
            session.flush()
        session.add(
            EpisodeArticle(
                episode_id=episode.id,
                article_id=article.id,
                source_id=source["source_id"],
                block=source["block"],
                rank=source["rank"],
                reason=source["reason"],
            )
        )
    target = data_dir / SAMPLE_AUDIO_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(SAMPLE_AUDIO, target)
    return episode
