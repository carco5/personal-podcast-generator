import re
from collections.abc import Callable
from datetime import UTC, datetime, time
from typing import Any

from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import Settings
from app.models import Article, Episode, Interest, PodcastSettings, User
from app.pipeline.checks import Judgement
from app.pipeline.common import PaidCall, Run
from app.pipeline.script import Script
from app.pipeline.selection import Picks
from app.pipeline.voice import ToneVoice, Voice
from app.sources.http import Fetcher


class FakeLlm:
    def __init__(self, responders: dict[type, Callable[[str], BaseModel]] | None = None) -> None:
        defaults = {Picks: pick_first, Script: write_from_plan, Judgement: approve_all}
        self.responders = defaults | (responders or {})
        self.prompts: list[tuple[type, str]] = []
        self.instructions: list[str] = []

    def parse[T: BaseModel](
        self, *, model: str, instructions: str, prompt: str, schema: type[T], effort: str
    ) -> tuple[T, PaidCall]:
        self.prompts.append((schema, prompt))
        self.instructions.append(instructions)
        call = PaidCall("openai", model, 0.0, 1, input_tokens=len(prompt) // 4, output_tokens=10)
        return self.responders[schema](prompt), call


def pick_first(prompt: str) -> Picks:
    blocks = []
    for section in prompt.split("\n## Block ")[1:]:
        key = section.split(":", 1)[0]
        wanted = int(re.search(r"Pick up to (\d+)", section).group(1))
        ids = re.findall(r"^\[(C\d+)\]", section, re.MULTILINE)[:wanted]
        stories = [{"source_ids": [temp], "reason": "fake"} for temp in ids]
        blocks.append({"key": key, "stories": stories})
    return Picks.model_validate({"blocks": blocks})


def write_from_plan(prompt: str) -> Script:
    segments: list[dict] = []
    for line in prompt.split("SOURCES")[0].splitlines():
        if found := re.match(r'- Segment "([^"]+)"', line):
            segments.append({"key": found.group(1), "turns": []})
        elif found := re.match(r"  - Story \d+: sources (.+)", line):
            ids = found.group(1).split(", ")
            segments[-1]["turns"].append(
                {"speaker": "host", "text": "Next story.", "source_ids": ids}
            )
    lead = segments[1]["turns"][0]["source_ids"]
    segments[0]["turns"] = [{"speaker": "host", "text": "Big news today.", "source_ids": lead}]
    segments[-1]["turns"] = [{"speaker": "analyst", "text": "See you tomorrow!", "source_ids": []}]
    return Script.model_validate({"title": "Test episode", "segments": segments})


def approve_all(prompt: str, flags: dict[str, str] | None = None) -> Judgement:
    turn_ids = re.findall(r"^\[(\w[\w-]*\.\d+)\] sources", prompt, re.MULTILINE)
    verdicts = [
        {"turn": turn, "verdict": (flags or {}).get(turn, "supported"), "explanation": "fake"}
        for turn in turn_ids
    ]
    return Judgement.model_validate({"verdicts": verdicts})


def make_listener(
    session: Session, interests: list[tuple[Any, ...]], length_minutes: int = 5
) -> tuple[User, PodcastSettings, list[Interest]]:
    user = User(email="listener@example.com", name="Listener")
    session.add(user)
    session.flush()
    podcast = PodcastSettings(
        user_id=user.id,
        show_name="Test Show",
        length_minutes=length_minutes,
        tone="casual",
        hosts=[
            {"role": "host", "name": "George", "personality": "Warm presenter."},
            {"role": "analyst", "name": "Sarah", "personality": "Sharp analyst."},
        ],
        schedule_days=[],
        schedule_time=time(7, 0),
        timezone="Europe/Madrid",
    )
    rows = []
    for topic, weight, *keywords in interests:
        kind = "custom" if keywords else "catalog"
        rows.append(
            Interest(
                user_id=user.id,
                kind=kind,
                topic=topic,
                weight=weight,
                keywords=keywords[0] if keywords else [],
            )
        )
    session.add_all([podcast, *rows])
    session.flush()
    return user, podcast, rows


def make_run(
    session: Session,
    user: User,
    podcast: PodcastSettings,
    interests: list[Interest],
    llm: FakeLlm | None = None,
    now: datetime | None = None,
    voice: Voice | None = None,
) -> Run:
    episode = Episode(user_id=user.id, trigger="manual", scheduled_for=func.now())
    session.add(episode)
    session.flush()
    return Run(
        session=session,
        episode=episode,
        podcast=podcast,
        interests=interests,
        config=Settings(_env_file=None, openai_api_key=None, guardian_api_key=None),
        llm=llm or FakeLlm(),
        voice=voice or ToneVoice(),
        fetcher=Fetcher(),
        now=now or datetime.now(UTC),
    )


def make_article(
    session: Session,
    source: str,
    title: str,
    published_at: datetime,
    *,
    body: str | None = None,
    meta: dict[str, Any] | None = None,
    fetched_at: datetime | None = None,
    path: str = "",
) -> Article:
    article = Article(
        source=source,
        kind="data" if meta else "article",
        official=bool(meta),
        language="en",
        url=f"https://example.com/{source}{path}/{len(title)}/{title.replace(' ', '-')}",
        title=title,
        body=body if body is not None else f"{title}. Body text.",
        published_at=published_at,
        meta=meta or {},
        fetched_at=fetched_at or published_at,
    )
    session.add(article)
    session.flush()
    return article
