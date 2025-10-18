"""Update_podium_foreign_key

Create Date: 2025-10-18 11:26:25.491895
"""

from collections.abc import Sequence
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pytest_alembic import MigrationContext

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d1079d6b8e6b"
down_revision: str | None = "c4812e1ab108"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(
        type_="primary",
        table_name="competition_sport_podium",
        constraint_name="competition_sport_podium_pkey",
    )
    op.create_primary_key(
        constraint_name="competition_sport_podium_pkey",
        table_name="competition_sport_podium",
        columns=["team_id", "sport_id", "edition_id", "school_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        type_="primary",
        table_name="competition_sport_podium",
        constraint_name="competition_sport_podium_pkey",
    )
    op.create_primary_key(
        constraint_name="competition_sport_podium_pkey",
        table_name="competition_sport_podium",
        columns=["sport_id", "edition_id", "school_id"],
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
