"""competition_ffsu_id

Create Date: 2025-09-28 18:40:58.803286
"""

from collections.abc import Sequence
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pytest_alembic import MigrationContext

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c4812e1ab108"
down_revision: str | None = "0064bf0a6f13"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_column("competition_school_extension", "ffsu_id")


def downgrade() -> None:
    op.add_column(
        "competition_school_extension",
        sa.Column("ffsu_id", sa.String(), nullable=True),
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
