"""empty message

Create Date: 2025-08-31 16:21:26.108997
"""

from collections.abc import Sequence
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pytest_alembic import MigrationContext

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ecd89212ca0"
down_revision: str | None = "e39b96af2ca0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "advert_adverts",
        sa.Column(
            "notification",
            sa.Boolean(),
            nullable=False,
            server_default="True",
        ),
    )
    op.add_column(
        "calendar_events",
        sa.Column(
            "notification",
            sa.Boolean(),
            nullable=False,
            server_default="True",
        ),
    )


def downgrade() -> None:
    op.drop_column(
        "advert_adverts",
        "notification",
    )
    op.drop_column(
        "calendar_events",
        "notification",
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
