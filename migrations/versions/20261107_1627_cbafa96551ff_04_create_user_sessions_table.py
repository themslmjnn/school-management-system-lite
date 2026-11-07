"""04_create_user_sessions_table

Revision ID: cbafa96551ff
Revises: 0afe9c99805c
Create Date: 2026-11-07 16:27:28.976482

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "cbafa96551ff"
down_revision: str | Sequence[str] | None = "0afe9c99805c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "user_sessions",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column(
            "access_token_version", sa.INTEGER(), nullable=False, server_default="1"
        ),
        sa.Column("refresh_token_hash", sa.String(), nullable=True),
        sa.Column(
            "refresh_token_expires_at", sa.DateTime(timezone=True), nullable=True
        ),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.String(length=255), nullable=True),
        sa.Column("last_active_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_user_sessions_user_id_users",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_user_sessions"),
        sa.UniqueConstraint("user_id", name="uq_user_sessions_user_id"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("user_sessions")
