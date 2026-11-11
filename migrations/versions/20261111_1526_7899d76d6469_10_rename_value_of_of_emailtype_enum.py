"""10_rename_value_of_of_emailtype_enum

Revision ID: 7899d76d6469
Revises: 4aa0af3ca596
Create Date: 2026-11-11 15:26:05.019797

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7899d76d6469"
down_revision: str | Sequence[str] | None = "4aa0af3ca596"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        "ALTER TYPE emailtype RENAME VALUE 'ADMIN_IDENTITY_OVERRIDE' TO 'ADMIN_USER_IDENTITY_OVERRIDE'"
    )
    op.execute(
        "ALTER TYPE emailtype RENAME VALUE 'ADMIN_CREDENTIALS_OVERRIDE' TO 'ADMIN_USER_EMAIL_OVERRIDE'"
    )
    op.execute(
        "ALTER TYPE emailtype RENAME VALUE 'PUBLIC_PASSWORD_RESET' TO 'FORGOT_PASSWORD_REQUEST'"
    )
    op.execute(
        "ALTER TYPE emailtype RENAME VALUE 'EMAIL_CHANGE' TO 'EMAIL_CHANGE_REQUEST'"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(
        "ALTER TYPE emailtype RENAME VALUE 'ADMIN_USER_IDENTITY_OVERRIDE' TO 'ADMIN_IDENTITY_OVERRIDE'"
    )
    op.execute(
        "ALTER TYPE emailtype RENAME VALUE 'ADMIN_USER_EMAIL_OVERRIDE' TO 'ADMIN_CREDENTIALS_OVERRIDE'"
    )
    op.execute(
        "ALTER TYPE emailtype RENAME VALUE 'FORGOT_PASSWORD_REQUEST' TO 'PUBLIC_PASSWORD_RESET'"
    )
    op.execute(
        "ALTER TYPE emailtype RENAME VALUE 'EMAIL_CHANGE_REQUEST' TO 'EMAIL_CHANGE'"
    )
