from datetime import datetime, time
from typing import Annotated, Literal, Self
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from app.catalog import CATALOG
from app.models import (
    EpisodeLength,
    EpisodeStatus,
    EpisodeTrigger,
    InterestKind,
    ListenKind,
    SourceKind,
    Stage,
    Tone,
    Weight,
)

ShortText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=60)]

HOST_ROLES = ["host", "analyst"]


class ReadModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# --- Settings ---


class Host(BaseModel):
    role: Literal["host", "analyst"]
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=30)]
    personality: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=300)
    ]


class PodcastSettingsUpdate(BaseModel):
    show_name: ShortText
    length_minutes: EpisodeLength
    tone: Tone
    hosts: list[Host]
    schedule_days: list[Annotated[int, Field(ge=1, le=7)]] = Field(max_length=7)
    schedule_time: time
    timezone: str

    @field_validator("hosts")
    @classmethod
    def two_fixed_hosts(cls, hosts: list[Host]) -> list[Host]:
        if [host.role for host in hosts] != HOST_ROLES:
            raise ValueError("hosts must be exactly one 'host' followed by one 'analyst'")
        return hosts

    @field_validator("schedule_days")
    @classmethod
    def unique_sorted_days(cls, days: list[int]) -> list[int]:
        return sorted(set(days))

    @field_validator("timezone")
    @classmethod
    def known_timezone(cls, name: str) -> str:
        try:
            ZoneInfo(name)
        except ZoneInfoNotFoundError, ValueError:
            raise ValueError(f"unknown time zone '{name}'") from None
        return name


class PodcastSettingsRead(PodcastSettingsUpdate, ReadModel):
    updated_at: datetime


# --- Interests ---


class InterestCreate(BaseModel):
    kind: InterestKind
    topic: ShortText
    keywords: list[ShortText] = Field(default_factory=list, max_length=10)
    weight: Weight = "medium"

    @model_validator(mode="after")
    def check_kind(self) -> Self:
        if self.kind == "catalog":
            if self.topic not in CATALOG:
                raise ValueError(f"'{self.topic}' is not in the catalog")
            if self.keywords:
                raise ValueError("catalog topics take no keywords")
        elif not self.keywords:
            raise ValueError("a custom topic needs at least one keyword")
        return self


class InterestUpdate(BaseModel):
    weight: Weight


class InterestRead(ReadModel):
    id: int
    kind: InterestKind
    topic: str
    keywords: list[str]
    weight: Weight
    created_at: datetime


# --- Episodes ---


class EpisodeRead(ReadModel):
    id: int
    status: EpisodeStatus
    trigger: EpisodeTrigger
    scheduled_for: datetime
    attempts: int
    status_reason: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    title: str | None
    duration_seconds: float | None
    stage: Stage | None = None
    news_as_of: datetime | None = None


class Chapter(BaseModel):
    key: str
    title: str
    start_seconds: float


class Turn(BaseModel):
    speaker: Literal["host", "analyst"]
    text: str
    source_ids: list[str]


class Section(BaseModel):
    key: str
    title: str
    turns: list[Turn]


class CitedSource(BaseModel):
    source_id: str
    section: str
    outlet: str
    official: bool
    kind: SourceKind
    title: str
    url: str
    published_at: datetime


class EpisodeDetail(EpisodeRead):
    chapters: list[Chapter]
    transcript: list[Section]
    sources: list[CitedSource]


class ListenEventCreate(BaseModel):
    kind: ListenKind
    position_seconds: float = Field(ge=0, le=3600)


class Generation(BaseModel):
    missing_keys: list[str]
    voice: Literal["tone", "elevenlabs"]
    next_episode_at: datetime | None


class EpisodePage(BaseModel):
    episodes: list[EpisodeRead]
    page_count: int
    next_page: int | None


class Health(BaseModel):
    status: Literal["ok"]
