"""empty message

Create Date: 2025-07-26 18:06:00.966810
"""

from collections.abc import Sequence
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pytest_alembic import MigrationContext

import sqlalchemy as sa
from alembic import op

from app.types.sqlalchemy import TZDateTime

# revision identifiers, used by Alembic.
revision: str = "52ce7195775f"
down_revision: str | None = "7da0e98a9e32"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "email_queue",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("subject", sa.String(), nullable=False),
        sa.Column("body", sa.String(), nullable=False),
        sa.Column("created_on", TZDateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "core_user_invitation",
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("default_group_id", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(
            ["default_group_id"],
            ["core_group.id"],
        ),
        sa.PrimaryKeyConstraint("email"),
    )
    op.add_column(
        "core_user_unconfirmed",
        sa.Column("default_group_id", sa.String(), nullable=True),
    )
    op.create_foreign_key(
        None,
        "core_user_unconfirmed",
        "core_group",
        ["default_group_id"],
        ["id"],
    )
    # ### end Alembic commands ###s


def downgrade() -> None:
    op.drop_table("email_queue")
    op.drop_table("core_user_invitation")
    op.drop_column("core_user_unconfirmed", "default_group_id")


def pre_test_upgrade(
    alembic_runner: "MigrationContext",
    alembic_connection: sa.Connection,
) -> None:
    pass


def test_upgrade(
    alembic_runner: "MigrationContext",
    alembic_connection: sa.Connection,
) -> None:
    pass
