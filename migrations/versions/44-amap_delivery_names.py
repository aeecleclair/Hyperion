"""empty message

Create Date: 2025-10-21 19:53:38.521697
"""

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pytest_alembic import MigrationContext

import sqlalchemy as sa
from alembic import op

from app.types.sqlalchemy import TZDateTime

# revision identifiers, used by Alembic.
revision: str = "9fc3dc926600"
down_revision: str | None = "d1079d6b8e6b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("amap_delivery", sa.Column("name", sa.String(), nullable=True))
    op.execute("UPDATE amap_delivery SET name = ''")
    op.alter_column("amap_delivery", "name", nullable=False)
    op.create_index(
        op.f("ix_amap_delivery_name"),
        "amap_delivery",
        ["name"],
        unique=False,
    )

    op.add_column(
        "amap_cash",
        sa.Column("last_order_date", TZDateTime(), nullable=True),
    )
    default_time = datetime(2025, 1, 1, tzinfo=UTC)
    op.execute(
        sa.text("UPDATE amap_cash SET last_order_date = :last_order_date").bindparams(
            sa.bindparam("last_order_date", value=default_time),
        ),
    )
    op.alter_column("amap_cash", "last_order_date", nullable=False)

    op.drop_column("amap_order", "delivery_date")


def downgrade() -> None:
    op.drop_column("amap_cash", "last_order_date")
    op.drop_column("amap_delivery", "name")
    op.add_column(
        "amap_order",
        sa.Column("delivery_date", TZDateTime(), nullable=True),
    )
    default_time = datetime(2025, 1, 1, tzinfo=UTC)
    op.execute(
        sa.text("UPDATE amap_order SET delivery_date = :delivery_date").bindparams(
            sa.bindparam("delivery_date", value=default_time),
        ),
    )
    op.alter_column("amap_order", "delivery_date", nullable=False)


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
