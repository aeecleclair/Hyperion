"""empty message

Create Date: 2025-10-21 19:53:38.521697
"""

from collections.abc import Sequence
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pytest_alembic import MigrationContext

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "562adbd796ae"
down_revision: str | None = "9fc3dc926600"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text("""
        UPDATE competition_match
        SET date = NOW()
        WHERE date IS NULL
        """),
    )
    conn.execute(
        sa.text("""
        DELETE FROM competition_school_product_quota
        WHERE quota IS NULL
        """),
    )
    op.alter_column("competition_match", "date", nullable=False)
    op.alter_column(
        "competition_school_product_quota",
        "quota",
        nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "competition_school_product_quota",
        "quota",
        nullable=True,
    )
    op.alter_column("competition_match", "date", nullable=True)


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
