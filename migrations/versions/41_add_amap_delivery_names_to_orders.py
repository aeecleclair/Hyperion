"""empty message

Create Date: 2025-09-12 11:21:06.877799
"""

from collections.abc import Sequence
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pytest_alembic import MigrationContext

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b72df3765853"
down_revision: str | None = "70f18009ac69"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("amap_order", sa.Column("delivery_name", sa.String(), nullable=True))
    op.execute("UPDATE amap_order SET delivery_name = ''")
    op.alter_column("amap_order", "delivery_name", nullable=False)


def downgrade() -> None:
    op.drop_column("amap_order", "delivery_name")


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
