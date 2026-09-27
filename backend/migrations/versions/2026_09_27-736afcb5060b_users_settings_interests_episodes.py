"""users settings interests episodes

Revision ID: 736afcb5060b
Revises:
Create Date: 2026-09-27 22:56:19.455235

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "736afcb5060b"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("email", name=op.f("uq_users_email")),
    )
    op.create_table(
        "episodes",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.Text(), server_default=sa.text("'queued'"), nullable=False),
        sa.Column("trigger", sa.Text(), nullable=False),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempts", sa.SmallInteger(), server_default=sa.text("0"), nullable=False),
        sa.Column("status_reason", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('queued', 'in_progress', 'completed', 'failed', 'skipped')",
            name=op.f("ck_episodes_status"),
        ),
        sa.CheckConstraint("trigger IN ('scheduled', 'manual')", name=op.f("ck_episodes_trigger")),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_episodes_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_episodes")),
        sa.UniqueConstraint(
            "user_id", "scheduled_for", name=op.f("uq_episodes_user_id_scheduled_for")
        ),
    )
    op.create_index(
        "uq_episodes_one_in_flight_per_user",
        "episodes",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('queued', 'in_progress')"),
    )
    op.create_table(
        "interests",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("topic", sa.Text(), nullable=False),
        sa.Column(
            "keywords", postgresql.ARRAY(sa.Text()), server_default=sa.text("'{}'"), nullable=False
        ),
        sa.Column("weight", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "(kind = 'catalog') = (cardinality(keywords) = 0)", name=op.f("ck_interests_keywords")
        ),
        sa.CheckConstraint("kind IN ('catalog', 'custom')", name=op.f("ck_interests_kind")),
        sa.CheckConstraint("weight IN ('low', 'medium', 'high')", name=op.f("ck_interests_weight")),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_interests_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_interests")),
        sa.UniqueConstraint("user_id", "topic", name=op.f("uq_interests_user_id_topic")),
    )
    op.create_table(
        "podcast_settings",
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("show_name", sa.Text(), nullable=False),
        sa.Column("length_minutes", sa.SmallInteger(), nullable=False),
        sa.Column("tone", sa.Text(), nullable=False),
        sa.Column("hosts", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("schedule_days", postgresql.ARRAY(sa.SmallInteger()), nullable=False),
        sa.Column("schedule_time", sa.Time(), nullable=False),
        sa.Column("timezone", sa.Text(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "tone IN ('casual', 'analytical')", name=op.f("ck_podcast_settings_tone")
        ),
        sa.CheckConstraint(
            "length_minutes IN (3, 5, 7)", name=op.f("ck_podcast_settings_length_minutes")
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_podcast_settings_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("user_id", name=op.f("pk_podcast_settings")),
    )


def downgrade() -> None:
    op.drop_table("podcast_settings")
    op.drop_table("interests")
    op.drop_index(
        "uq_episodes_one_in_flight_per_user",
        table_name="episodes",
        postgresql_where=sa.text("status IN ('queued', 'in_progress')"),
    )
    op.drop_table("episodes")
    op.drop_table("users")
