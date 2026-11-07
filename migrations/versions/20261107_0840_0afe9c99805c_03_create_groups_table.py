"""03_create_groups_table

Revision ID: 0afe9c99805c
Revises: 4b36bc9a6658
Create Date: 2026-11-07 08:40:08.850899

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0afe9c99805c"
down_revision: str | Sequence[str] | None = "4b36bc9a6658"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "groups",
        sa.Column("name", sa.String(length=10), nullable=False),
        sa.Column("academic_year", sa.String(length=10), nullable=False),
        sa.Column("grade_level", sa.Integer(), nullable=False),
        sa.Column("max_capacity", sa.Integer(), nullable=False, server_default="25"),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_groups")),
        sa.UniqueConstraint(
            "name", "academic_year", name="uq_groups_name_academic_year"
        ),
    )

    op.create_index(op.f("ix_groups_name"), "groups", ["name"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_groups_name"), "groups")

    op.drop_table("groups")
