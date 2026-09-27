from datetime import datetime, time
from typing import Literal, get_args

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    MetaData,
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
    )
