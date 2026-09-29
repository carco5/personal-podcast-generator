"""split fc-barcelona interest

Revision ID: b07edd4c08e6
Revises: e3d606ed94cd
Create Date: 2026-09-29 20:35:29.244068

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b07edd4c08e6"
down_revision: str | Sequence[str] | None = "e3d606ed94cd"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "INSERT INTO interests (user_id, kind, topic, keywords, weight, created_at) "
        "SELECT user_id, kind, 'fc-barcelona-basketball', keywords, weight, created_at "
        "FROM interests WHERE topic = 'fc-barcelona'"
    )
    op.execute("UPDATE interests SET topic = 'fc-barcelona-football' WHERE topic = 'fc-barcelona'")


def downgrade() -> None:
    op.execute(
        "DELETE FROM interests b WHERE b.topic = 'fc-barcelona-basketball' AND EXISTS "
        "(SELECT 1 FROM interests f "
        "WHERE f.user_id = b.user_id AND f.topic = 'fc-barcelona-football')"
    )
    op.execute(
        "UPDATE interests SET topic = 'fc-barcelona' "
        "WHERE topic IN ('fc-barcelona-football', 'fc-barcelona-basketball')"
    )
