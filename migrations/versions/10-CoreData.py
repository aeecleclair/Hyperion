"""Add CoreData table

Create Date: 2024-04-21 02:08:19.548067
"""

from collections.abc import Sequence
from typing import TYPE_CHECKING

import sqlalchemy as sa
from alembic import op

if TYPE_CHECKING:
    from pytest_alembic import MigrationContext

# revision identifiers, used by Alembic.
revision: str = "36a686097ce6"
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


def downgrade() -> None:
    op.drop_table("core_data")


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
