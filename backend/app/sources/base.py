import re
from abc import ABC, abstractmethod
from collections.abc import Iterator
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
