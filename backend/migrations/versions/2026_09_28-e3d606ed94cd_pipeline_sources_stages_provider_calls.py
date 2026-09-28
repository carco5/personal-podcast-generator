"""pipeline sources stages provider calls

Revision ID: e3d606ed94cd
Revises: 736afcb5060b
Create Date: 2026-09-28 11:26:13.949220

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "e3d606ed94cd"
down_revision: str | Sequence[str] | None = "736afcb5060b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "articles",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("official", sa.Boolean(), nullable=False),
        sa.Column("language", sa.Text(), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "meta",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
        sa.Column(
            "fetched_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("kind IN ('article', 'data')", name=op.f("ck_articles_kind")),
        sa.CheckConstraint("language IN ('en', 'es')", name=op.f("ck_articles_language")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_articles")),
        sa.UniqueConstraint("url", name=op.f("uq_articles_url")),
    )
    op.create_index(
        "ix_articles_source_published_at", "articles", ["source", "published_at"], unique=False
    )
    op.create_table(
        "episode_articles",
        sa.Column("episode_id", sa.BigInteger(), nullable=False),
        sa.Column("article_id", sa.BigInteger(), nullable=False),
        sa.Column("source_id", sa.Text(), nullable=False),
        sa.Column("block", sa.Text(), nullable=False),
        sa.Column("rank", sa.SmallInteger(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["article_id"], ["articles.id"], name=op.f("fk_episode_articles_article_id_articles")
        ),
        sa.ForeignKeyConstraint(
            ["episode_id"],
            ["episodes.id"],
            name=op.f("fk_episode_articles_episode_id_episodes"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("episode_id", "article_id", name=op.f("pk_episode_articles")),
        sa.UniqueConstraint(
            "episode_id", "source_id", name=op.f("uq_episode_articles_episode_id_source_id")
        ),
    )
    op.create_index(
        op.f("ix_episode_articles_article_id"), "episode_articles", ["article_id"], unique=False
    )
    op.create_table(
        "stage_runs",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("episode_id", sa.BigInteger(), nullable=False),
        sa.Column("attempt", sa.SmallInteger(), nullable=False),
        sa.Column("stage", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column(
            "details",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "stage IN ('fetch', 'select', 'write', 'check', 'voice', 'master')",
            name=op.f("ck_stage_runs_stage"),
        ),
        sa.CheckConstraint(
            "status IN ('in_progress', 'completed', 'failed')", name=op.f("ck_stage_runs_status")
        ),
        sa.ForeignKeyConstraint(
            ["episode_id"],
            ["episodes.id"],
            name=op.f("fk_stage_runs_episode_id_episodes"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_stage_runs")),
    )
    op.create_index(op.f("ix_stage_runs_episode_id"), "stage_runs", ["episode_id"], unique=False)
    op.create_table(
        "provider_calls",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("stage_run_id", sa.BigInteger(), nullable=False),
        sa.Column("provider", sa.Text(), nullable=False),
        sa.Column("model", sa.Text(), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("characters", sa.Integer(), nullable=True),
        sa.Column("cost_usd", sa.Numeric(precision=10, scale=6), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "(provider = 'openai' AND input_tokens IS NOT NULL AND output_tokens IS NOT NULL"
            " AND characters IS NULL)"
            " OR (provider = 'elevenlabs' AND characters IS NOT NULL"
            " AND input_tokens IS NULL AND output_tokens IS NULL)",
            name=op.f("ck_provider_calls_usage"),
        ),
        sa.CheckConstraint(
            "provider IN ('openai', 'elevenlabs')", name=op.f("ck_provider_calls_provider")
        ),
        sa.ForeignKeyConstraint(
            ["stage_run_id"],
            ["stage_runs.id"],
            name=op.f("fk_provider_calls_stage_run_id_stage_runs"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_provider_calls")),
    )
    op.create_index(
        op.f("ix_provider_calls_stage_run_id"), "provider_calls", ["stage_run_id"], unique=False
    )
    op.add_column("episodes", sa.Column("title", sa.Text(), nullable=True))
    op.add_column(
        "episodes", sa.Column("plan", postgresql.JSONB(astext_type=sa.Text()), nullable=True)
    )
    op.add_column(
        "episodes", sa.Column("script", postgresql.JSONB(astext_type=sa.Text()), nullable=True)
    )
    op.add_column("episodes", sa.Column("audio_path", sa.Text(), nullable=True))
    op.add_column("episodes", sa.Column("duration_seconds", sa.Double(), nullable=True))
    op.add_column(
        "episodes", sa.Column("chapters", postgresql.JSONB(astext_type=sa.Text()), nullable=True)
    )
    # Autogenerate does not detect new CHECK constraints on an existing table.
    op.create_check_constraint(
        op.f("ck_episodes_audio"), "episodes", "(status = 'completed') = (audio_path IS NOT NULL)"
    )
    op.create_check_constraint(
        op.f("ck_episodes_reason"),
        "episodes",
        "(status IN ('failed', 'skipped')) = (status_reason IS NOT NULL)",
    )


def downgrade() -> None:
    op.drop_constraint(op.f("ck_episodes_reason"), "episodes", type_="check")
    op.drop_constraint(op.f("ck_episodes_audio"), "episodes", type_="check")
    op.drop_column("episodes", "chapters")
    op.drop_column("episodes", "duration_seconds")
    op.drop_column("episodes", "audio_path")
    op.drop_column("episodes", "script")
    op.drop_column("episodes", "plan")
    op.drop_column("episodes", "title")
    op.drop_index(op.f("ix_provider_calls_stage_run_id"), table_name="provider_calls")
    op.drop_table("provider_calls")
    op.drop_index(op.f("ix_stage_runs_episode_id"), table_name="stage_runs")
    op.drop_table("stage_runs")
    op.drop_index(op.f("ix_episode_articles_article_id"), table_name="episode_articles")
    op.drop_table("episode_articles")
    op.drop_index("ix_articles_source_published_at", table_name="articles")
    op.drop_table("articles")
