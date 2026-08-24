from collections.abc import Sequence
from typing import TYPE_CHECKING

from app.types.sqlalchemy import TZDateTime

if TYPE_CHECKING:
    from pytest_alembic import MigrationContext

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e0e6f306bed7"
down_revision: str | None = "dd905b1f5f57"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:

    op.add_column(
        "raid_security_file",
        sa.Column(
            "consent_given",
            sa.Boolean(),
            nullable=False,
            server_default="False",
        ),
    )
    op.add_column(
        "raid_security_file",
        sa.Column("consent_given_at", TZDateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_column("raid_security_file", "consent_given")
    op.drop_column("raid_security_file", "consent_given_at")


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
