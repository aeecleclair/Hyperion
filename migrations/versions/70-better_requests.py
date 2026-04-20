"""empty message

Create Date: 2026-04-20 00:51:44.716180
"""

from collections.abc import Sequence
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pytest_alembic import MigrationContext

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9bb79b2466f9"
down_revision: str | None = "c4d2aa4e6f1b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            DELETE FROM pg_enum WHERE enumtypid = (
                SELECT oid FROM pg_type WHERE typname = 'requeststatus'
            ) AND enumlabel = 'EXPIRED'
            """,
        ),
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            ALTER TYPE requeststatus ADD VALUE IF NOT EXISTS 'EXPIRED'
            """,
        ),
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
