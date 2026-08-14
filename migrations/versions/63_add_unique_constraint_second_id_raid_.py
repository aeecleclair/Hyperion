"""add_unique_constraint_second_id_raid_team

Create Date: 2026-08-07 13:00:39.510717
"""

from collections.abc import Sequence
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pytest_alembic import MigrationContext

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "63"
down_revision: str | None = "b23c5f9d8a42"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add unique constraint on second_id + edition_id to prevent race condition
    # when two users try to join the same team simultaneously
    op.create_unique_constraint(
        "uq_raid_team_second_id_edition_id",
        "raid_team",
        ["second_id", "edition_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_raid_team_second_id_edition_id",
        "raid_team",
        type_="unique",
    )


def pre_test_upgrade(
    alembic_runner: "MigrationContext",
    alembic_connection: sa.Connection,
) -> None:
    # No pre-test data needed - constraint is new
    pass


def test_upgrade(
    alembic_runner: "MigrationContext",
    alembic_connection: sa.Connection,
) -> None:
    # Verify the unique constraint was created
    result = alembic_connection.execute(
        sa.text(
            """
            SELECT conname FROM pg_constraint
            WHERE conname = 'uq_raid_team_second_id_edition_id'
            AND contype = 'u'
            """,
        ),
    ).fetchall()
    assert len(result) == 1
