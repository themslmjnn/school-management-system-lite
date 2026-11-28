"""14_rename_value_of_emailtype_enum

Revision ID: 10117fa122ae
Revises: 9acda9797c30
Create Date: 2026-11-28 09:33:28.190795

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "10117fa122ae"
down_revision: str | Sequence[str] | None = "9acda9797c30"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        "ALTER TYPE emailtype RENAME VALUE 'ADMIN_ACCOUNT_ACTIVATION' TO 'ADMIN_ACCOUNT_REACTIVATION'"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(
        "ALTER TYPE emailtype RENAME VALUE 'ADMIN_ACCOUNT_REACTIVATION' TO 'ADMIN_ACCOUNT_ACTIVATION'"
    )
