"""greencode

Create Date: 2024-05-10 19:23:04.089249
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "da7e4338129d"
down_revision: str | None = "c3acc9b8dd98"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "core_data",
        sa.Column("schema", sa.String(), nullable=False),
        sa.Column("data", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("schema"),
    )
    op.create_table(
        "greencode_items",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("qr_code_content", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("content", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("qr_code_content"),
    )
    op.create_index(
        op.f("ix_greencode_items_id"),
        "greencode_items",
        ["id"],
        unique=True,
    )
    op.create_table(
        "greencode_memberships",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("item_id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["item_id"], ["greencode_items.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["core_user.id"]),
        sa.PrimaryKeyConstraint("id", "item_id", "user_id"),
    )
    op.create_index(
        op.f("ix_greencode_memberships_id"),
        "greencode_memberships",
        ["id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_greencode_memberships_id"),
        table_name="greencode_memberships",
    )
    op.drop_table("greencode_memberships")
    op.drop_index(op.f("ix_greencode_items_id"), table_name="greencode_items")
    op.drop_table("greencode_items")
    op.drop_table("core_data")
