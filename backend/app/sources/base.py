import re
from abc import ABC, abstractmethod
from collections import Counter
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Any

import trafilatura
from pydantic import BaseModel, Field

from app.models import Language, SourceKind
from app.sources.http import Fetcher

MIN_BODY_CHARS = 500
MAX_BODY_CHARS = 8_000
MAX_AGE = timedelta(days=4)


class SourceItem(BaseModel):
    url: str
    title: str
    body: str
    published_at: datetime
    kind: SourceKind = "article"
    meta: dict[str, Any] = Field(default_factory=dict)


class Source(ABC):
    """A news or data provider behind one interface (D4)."""

    key: str
    language: Language
    official: bool

    @abstractmethod
    def items(self, fetcher: Fetcher, known: set[str]) -> Iterator[SourceItem]:
        """Yield the source's recent items, skipping articles whose URL is already known."""


def extract_text(html: str, noise: re.Pattern[str] | None = None) -> str:
    """The article text of an HTML page, without noise lines, capped at MAX_BODY_CHARS."""
    text = trafilatura.extract(html, include_comments=False, include_tables=False) or ""
    if noise is not None:
        text = "\n".join(line for line in text.splitlines() if not noise.search(line))
    return text[:MAX_BODY_CHARS]


def is_recent(published_at: datetime, now: datetime) -> bool:
    return now - published_at <= MAX_AGE


def parse_datetime(value: str) -> datetime:
    moment = datetime.fromisoformat(value)
    return moment if moment.tzinfo is not None else moment.replace(tzinfo=UTC)


def spoken_date(day: date) -> str:
    return f"{day:%A} {day.day} {day:%B} {day.year}"


def count(number: int, singular: str, plural: str | None = None) -> str:
    return f"{number} {singular}" if number == 1 else f"{number} {plural or singular + 's'}"


def gap_to_leader(points: int, leader: int, *, first: bool) -> str:
    if first:
        return ""
    gap = leader - points
    if gap == 0:
        return ", level on points with the leader"
    return f", {count(gap, 'point')} behind the leader"


@dataclass(frozen=True)
class Goal:
    team: str
    player: str
    minute: int
    penalty: bool = False
    assist: str = ""
    own_goal: bool = False


GOAL_LABELS = {2: "a brace", 3: "a hat-trick"}


def goals_sentence(goals: list[Goal], teams: list[str]) -> str:
    in_order = sorted(goals, key=lambda goal: goal.minute)
    parts = []
    for name in teams:
        mine = [goal for goal in in_order if goal.team == name and not goal.own_goal]
        if not mine:
            continue
        minutes: dict[str, list[str]] = {}
        for goal in mine:
            minutes.setdefault(goal.player, []).append(
                f"{goal.minute}'" + (" penalty" if goal.penalty else "")
            )
        scorers = ", ".join(
            f"{p} {len(m)}{f', {GOAL_LABELS[len(m)]}' if len(m) in GOAL_LABELS else ''}"
            f" ({', '.join(m)})"
            for p, m in minutes.items()
        )
        text = f"{name} goals: {scorers}."
        assists = Counter(goal.assist for goal in mine if goal.assist)
        if assists:
            text += " Assists: " + ", ".join(f"{p} {n}" for p, n in assists.items()) + "."
        parts.append(text)
    own = [f"{goal.player} ({goal.minute}')" for goal in in_order if goal.own_goal]
    if own:
        parts.append(f"Own goals: {', '.join(own)}.")
    return " ".join(parts)
