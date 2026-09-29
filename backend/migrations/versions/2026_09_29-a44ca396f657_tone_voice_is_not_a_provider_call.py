"""tone voice is not a provider call

Revision ID: a44ca396f657
Revises: a5739803b67f
Create Date: 2026-09-29 23:20:07.768037

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a44ca396f657"
down_revision: str | Sequence[str] | None = "a5739803b67f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("DELETE FROM provider_calls WHERE model = 'tone-for-development'")


def downgrade() -> None:
    # The deleted rows were never provider calls, so there is nothing to restore.
    pass
