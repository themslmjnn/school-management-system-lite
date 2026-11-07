"""08_add_scheduled_for_column_to_emails_table

Revision ID: 6f96c4c58c44
Revises: e2a8f7cce659
Create Date: 2026-11-07 23:46:13.105638

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "6f96c4c58c44"
down_revision: str | Sequence[str] | None = "e2a8f7cce659"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "emails",
        sa.Column(
            "scheduled_for",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("emails", "scheduled_for")
