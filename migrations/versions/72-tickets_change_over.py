"""empty message

Create Date: 2026-06-07 17:43:34.457871
"""

from collections.abc import Sequence
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pytest_alembic import MigrationContext

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "af6920fed071"
down_revision: str | None = "3108c3bc5425"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "tickets_change_over_invitation",
        sa.Column("ticket_id", sa.Uuid(), nullable=False),
        sa.Column("new_user_id", sa.String(), nullable=False),
        sa.Column("token", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["new_user_id"], ["core_user.id"]),
        sa.ForeignKeyConstraint(["ticket_id"], ["tickets_checkout.id"]),
        sa.PrimaryKeyConstraint("ticket_id"),
    )


def downgrade() -> None:
    op.drop_table("tickets_change_over_invitation")


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
