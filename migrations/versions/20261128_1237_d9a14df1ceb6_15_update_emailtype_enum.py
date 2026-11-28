"""15_update_emailtype_enum

Revision ID: d9a14df1ceb6
Revises: 10117fa122ae
Create Date: 2026-11-28 12:37:47.065524

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d9a14df1ceb6"
down_revision: str | Sequence[str] | None = "10117fa122ae"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        "ALTER TYPE emailtype RENAME VALUE 'PASSWORD_CHANGE_CONFIRMATION' TO 'PASSWORD_CHANGED_NOTIFICATION'"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(
        "ALTER TYPE emailtype RENAME VALUE 'PASSWORD_CHANGED_NOTIFICATION' TO 'PASSWORD_CHANGE_CONFIRMATION'"
    )
