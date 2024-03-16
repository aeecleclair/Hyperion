"""7-visibility

Revision ID: 7e8b1b7c2f4a
Revises: 6afc765adaa2
Create Date: 2024-03-16 14:01:13.392655

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7e8b1b7c2f4a"
down_revision: str | None = "6afc765adaa2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "module_awareness",
        sa.Column("root", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("root"),
    )
    # We want to drop existing module visibilities to create them again
    # using module awareness objects
    op.drop_table("module_visibility")
    op.create_table(
        "module_visibility",
        sa.Column("root", sa.String(), nullable=False),
        sa.Column("allowed_group_id", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("root", "allowed_group_id"),
    )


def downgrade() -> None:
    op.drop_table("module_awareness")
