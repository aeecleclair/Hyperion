"""add product needs_validation

Create Date: 2025-08-18 16:04:30.438478
"""

from collections.abc import Sequence
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pytest_alembic import MigrationContext

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "98e2557c00c8"
down_revision: str | None = "7da0e98a9e32"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "cdr_product",
        sa.Column("needs_validation", sa.Boolean(), nullable=True),
    )
    op.execute("UPDATE cdr_product SET needs_validation = true")
    op.alter_column("cdr_product", "needs_validation", nullable=False)


def downgrade() -> None:
    op.drop_column("cdr_product", "needs_validation")


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
