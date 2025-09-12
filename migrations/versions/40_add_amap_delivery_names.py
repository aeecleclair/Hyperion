"""empty message

Create Date: 2025-09-10 11:38:10.273001
"""

from collections.abc import Sequence
from typing import TYPE_CHECKING, Union

if TYPE_CHECKING:
    from pytest_alembic import MigrationContext

import sqlalchemy as sa
from alembic import op

from app.types.sqlalchemy import TZDateTime

# revision identifiers, used by Alembic.
revision: str = "70f18009ac69"
down_revision: str | None = "2880c583d7f1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("amap_delivery", sa.Column("name", sa.String(), nullable=True))
    op.execute("UPDATE amap_delivery SET name = ''")
    op.alter_column("amap_delivery", "name", nullable=False)


def downgrade() -> None:
    op.drop_column("amap_delivery", "name")


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
