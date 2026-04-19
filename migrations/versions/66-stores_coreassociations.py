"""empty message

Create Date: 2026-03-01 11:41:22.994301
"""

from collections.abc import Sequence
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pytest_alembic import MigrationContext

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "146db8dcb23e"
down_revision: str | None = "562adbd796ae"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "mypayment_store",
        sa.Column(
            "association_id",
            sa.Uuid(),
            nullable=True,
        ),
    )
    op.create_foreign_key(
        None,
        "mypayment_store",
        "associations_associations",
        ["association_id"],
        ["id"],
    )
    op.create_unique_constraint(None, "mypayment_store", ["association_id"])


def downgrade() -> None:
    op.drop_constraint(
        "mypayment_store_association_id_fkey",
        "mypayment_store",
        type_="foreignkey",
    )
    op.drop_column("mypayment_store", "association_id")


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
