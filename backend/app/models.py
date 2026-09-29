from datetime import datetime, time
from decimal import Decimal
from typing import Any, Literal, get_args

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Double,
    ForeignKey,
    Identity,
    Index,
    Integer,
    MetaData,
    Numeric,
    SmallInteger,
    Text,
    Time,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

EpisodeStatus = Literal["queued", "in_progress", "completed", "failed", "skipped"]
EpisodeTrigger = Literal["scheduled", "manual"]
EpisodeLength = Literal[3, 5, 7]
Tone = Literal["casual", "analytical"]
InterestKind = Literal["catalog", "custom"]
Weight = Literal["low", "medium", "high"]
SourceKind = Literal["article", "data"]
Language = Literal["en", "es"]
Stage = Literal["fetch", "select", "write", "check", "voice", "master"]
StageStatus = Literal["in_progress", "completed", "failed"]
Provider = Literal["openai", "elevenlabs"]
ListenKind = Literal["play", "heartbeat"]

# Deterministic constraint names, so migrations can refer to them.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_N_label)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


def allowed_values(column: str, values: object) -> CheckConstraint:
    """CHECK constraint limiting a column to the values of a Literal type."""
    sql_values = ", ".join(f"'{v}'" if isinstance(v, str) else str(v) for v in get_args(values))
    return CheckConstraint(f"{column} IN ({sql_values})", name=column)


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    email: Mapped[str] = mapped_column(Text, unique=True)
    name: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    is_synthetic: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))


class PodcastSettings(Base):
    __tablename__ = "podcast_settings"

    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    show_name: Mapped[str] = mapped_column(Text)
    length_minutes: Mapped[int] = mapped_column(SmallInteger)
    tone: Mapped[str] = mapped_column(Text)
    hosts: Mapped[list[dict[str, str]]] = mapped_column(JSONB)
    schedule_days: Mapped[list[int]] = mapped_column(ARRAY(SmallInteger))
    schedule_time: Mapped[time] = mapped_column(Time)
    timezone: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        allowed_values("length_minutes", EpisodeLength),
        allowed_values("tone", Tone),
    )


class Interest(Base):
    __tablename__ = "interests"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    kind: Mapped[str] = mapped_column(Text)
    topic: Mapped[str] = mapped_column(Text)
    keywords: Mapped[list[str]] = mapped_column(ARRAY(Text), server_default=text("'{}'"))
    weight: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("user_id", "topic"),
        allowed_values("kind", InterestKind),
        allowed_values("weight", Weight),
        CheckConstraint("(kind = 'catalog') = (cardinality(keywords) = 0)", name="keywords"),
    )


class Episode(Base):
    __tablename__ = "episodes"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    status: Mapped[str] = mapped_column(Text, server_default=text("'queued'"))
    trigger: Mapped[str] = mapped_column(Text)
    scheduled_for: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    attempts: Mapped[int] = mapped_column(SmallInteger, server_default=text("0"))
    status_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    title: Mapped[str | None] = mapped_column(Text)
    plan: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    script: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    audio_path: Mapped[str | None] = mapped_column(Text)
    duration_seconds: Mapped[float | None] = mapped_column(Double)
    chapters: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB)

    __table_args__ = (
        UniqueConstraint("user_id", "scheduled_for"),
        # At most one episode in flight per user, so a double click never pays for voice twice.
        Index(
            "uq_episodes_one_in_flight_per_user",
            "user_id",
            unique=True,
            postgresql_where=text("status IN ('queued', 'in_progress')"),
        ),
        allowed_values("status", EpisodeStatus),
        allowed_values("trigger", EpisodeTrigger),
        CheckConstraint("(status = 'completed') = (audio_path IS NOT NULL)", name="audio"),
        CheckConstraint(
            "(status IN ('failed', 'skipped')) = (status_reason IS NOT NULL)", name="reason"
        ),
    )


class Article(Base):
    __tablename__ = "articles"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    source: Mapped[str] = mapped_column(Text)
    kind: Mapped[str] = mapped_column(Text)
    official: Mapped[bool] = mapped_column(Boolean)
    language: Mapped[str] = mapped_column(Text)
    url: Mapped[str] = mapped_column(Text, unique=True)
    title: Mapped[str] = mapped_column(Text)
    body: Mapped[str] = mapped_column(Text)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    meta: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default=text("'{}'"))
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        allowed_values("kind", SourceKind),
        allowed_values("language", Language),
        Index("ix_articles_source_published_at", "source", "published_at"),
    )


class EpisodeArticle(Base):
    __tablename__ = "episode_articles"

    episode_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("episodes.id", ondelete="CASCADE"), primary_key=True
    )
    article_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("articles.id"), primary_key=True)
    source_id: Mapped[str] = mapped_column(Text)
    block: Mapped[str] = mapped_column(Text)
    rank: Mapped[int] = mapped_column(SmallInteger)
    reason: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        UniqueConstraint("episode_id", "source_id"),
        Index(None, "article_id"),
    )


class StageRun(Base):
    __tablename__ = "stage_runs"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    episode_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("episodes.id", ondelete="CASCADE")
    )
    attempt: Mapped[int] = mapped_column(SmallInteger)
    stage: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error: Mapped[str | None] = mapped_column(Text)
    details: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default=text("'{}'"))

    __table_args__ = (
        allowed_values("stage", Stage),
        allowed_values("status", StageStatus),
        Index(None, "episode_id"),
    )


class ProviderCall(Base):
    __tablename__ = "provider_calls"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    stage_run_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("stage_runs.id", ondelete="CASCADE")
    )
    provider: Mapped[str] = mapped_column(Text)
    model: Mapped[str] = mapped_column(Text)
    input_tokens: Mapped[int | None] = mapped_column(Integer)
    output_tokens: Mapped[int | None] = mapped_column(Integer)
    characters: Mapped[int | None] = mapped_column(Integer)
    cost_usd: Mapped[Decimal] = mapped_column(Numeric(10, 6))
    latency_ms: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        allowed_values("provider", Provider),
        CheckConstraint(
            "(provider = 'openai' AND input_tokens IS NOT NULL AND output_tokens IS NOT NULL"
            " AND characters IS NULL)"
            " OR (provider = 'elevenlabs' AND characters IS NOT NULL"
            " AND input_tokens IS NULL AND output_tokens IS NULL)",
            name="usage",
        ),
        Index(None, "stage_run_id"),
    )


class ListenEvent(Base):
    __tablename__ = "listen_events"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    episode_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("episodes.id", ondelete="CASCADE")
    )
    kind: Mapped[str] = mapped_column(Text)
    position_seconds: Mapped[float] = mapped_column(Double)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        allowed_values("kind", ListenKind),
        CheckConstraint("position_seconds >= 0", name="position"),
        Index(None, "episode_id"),
    )
