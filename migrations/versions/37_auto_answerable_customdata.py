"""auto-answerable customdata

Create Date: 2025-08-20 14:06:53.519826
"""

from collections.abc import Sequence
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pytest_alembic import MigrationContext

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "06c94803745b"
down_revision: str | None = "98e2557c00c8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "cdr_customdata_field",
        sa.Column("can_user_answer", sa.Boolean(), nullable=True),
    )
    op.execute("UPDATE cdr_customdata_field SET can_user_answer = false")
    op.alter_column("cdr_customdata_field", "can_user_answer", nullable=False)


def downgrade() -> None:
    op.drop_column("cdr_customdata_field", "needs_validation")


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
