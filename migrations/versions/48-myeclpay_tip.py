"""empty message

Create Date: 2025-12-07 17:12:36.572793
"""

from collections.abc import Sequence
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pytest_alembic import MigrationContext

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8f97a0e41c9b"
down_revision: str | None = "12ceba87cf"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "payment_checkout_payment",
        sa.Column("tip_amount", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("payment_checkout_payment", "tip_amount")


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
