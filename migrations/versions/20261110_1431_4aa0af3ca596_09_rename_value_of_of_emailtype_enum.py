"""09_rename_value_of_of_emailtype_enum

Revision ID: 4aa0af3ca596
Revises: 6f96c4c58c44
Create Date: 2026-11-10 14:31:24.518442

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4aa0af3ca596"
down_revision: str | Sequence[str] | None = "6f96c4c58c44"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        "ALTER TYPE emailtype RENAME VALUE 'ADMIN_PROFILE_OVERRIDE' TO 'ADMIN_IDENTITY_OVERRIDE'"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(
        "ALTER TYPE emailtype RENAME VALUE 'ADMIN_IDENTITY_OVERRIDE' TO 'ADMIN_PROFILE_OVERRIDE'"
    )
