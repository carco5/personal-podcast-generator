from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from app.config import Settings
from app.models import Episode, Interest, PodcastSettings, Provider
from app.sources.http import Fetcher

if TYPE_CHECKING:
    from app.pipeline.llm import Llm
    from app.pipeline.voice import Voice


@dataclass(frozen=True)
class PaidCall:
    provider: Provider
    model: str
    cost_usd: float
    latency_ms: int
    input_tokens: int | None = None
    output_tokens: int | None = None
    characters: int | None = None


@dataclass
class Run:
    session: Session
    episode: Episode
    podcast: PodcastSettings
    interests: list[Interest]
    config: Settings
    llm: Llm
    voice: Voice
    fetcher: Fetcher
    now: datetime
    calls: list[PaidCall] = field(default_factory=list)


class EpisodeSkipped(Exception):
    """There is nothing new to tell: the episode ends as skipped, with this reason."""


class StageFailed(Exception):
    """A stage could not finish: the episode ends as failed, with this reason."""

    def __init__(self, reason: str, details: dict | None = None) -> None:
        super().__init__(reason)
        self.details = details or {}
