"""fix uuid type

Create Date: 2024-05-22 23:18:24.002804
"""

from collections.abc import Sequence
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pytest_alembic import MigrationContext

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7b078dd0e7e4"
down_revision: str | None = "fce1716123e2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "ph_papers",
        "id",
        type_=sa.Uuid(),
        postgresql_using="id::uuid",
    )
    op.drop_index("ix_ph_papers_id", table_name="ph_papers")


def downgrade() -> None:
    op.create_index("ix_ph_papers_id", "ph_papers", ["id"], unique=False)
    op.alter_column(
        "ph_papers",
        "id",
        type_=sa.String(),
    )


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
