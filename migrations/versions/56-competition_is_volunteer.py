"""Add is_volunteer column to competition_user and volunteer value to productpublictype enum

Create Date: 2026-02-24 12:00:00.000000
"""

from collections.abc import Sequence
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pytest_alembic import MigrationContext
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "562adbd796ae"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "competition_user",
        sa.Column(
            "is_volunteer",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "competition_user",
        sa.Column(
            "cancelled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.execute("ALTER TYPE productpublictype ADD VALUE IF NOT EXISTS 'volunteer'")


def downgrade() -> None:
    op.drop_column("competition_user", "is_volunteer")
    op.drop_column("competition_user", "cancelled")


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
