"""listen events

Revision ID: a5739803b67f
Revises: b07edd4c08e6
Create Date: 2026-09-29 20:45:32.364937

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a5739803b67f"
down_revision: str | Sequence[str] | None = "b07edd4c08e6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "listen_events",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("episode_id", sa.BigInteger(), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("position_seconds", sa.Double(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("kind IN ('play', 'heartbeat')", name=op.f("ck_listen_events_kind")),
        sa.CheckConstraint("position_seconds >= 0", name=op.f("ck_listen_events_position")),
        sa.ForeignKeyConstraint(
            ["episode_id"],
            ["episodes.id"],
            name=op.f("fk_listen_events_episode_id_episodes"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_listen_events")),
    )
    op.create_index(
        op.f("ix_listen_events_episode_id"), "listen_events", ["episode_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_listen_events_episode_id"), table_name="listen_events")
    op.drop_table("listen_events")
