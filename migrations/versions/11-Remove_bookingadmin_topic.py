"""Remove bookingadmin topic

Create Date: 2024-05-13 13:40:36.649220
"""

from collections.abc import Sequence
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pytest_alembic import MigrationContext

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e22bfe152f72"
down_revision: str | None = "36a686097ce6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "notification_topic_membership",
        "topic",
        existing_type=sa.VARCHAR(length=12),
        type_=sa.Enum(
            "cinema",
            "advert",
            "amap",
            "booking",
            "event",
            "loan",
            "raffle",
            "vote",
            name="topic",
        ),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "notification_topic_membership",
        "topic",
        existing_type=sa.VARCHAR(length=12),
        type_=sa.Enum(
            "cinema",
            "advert",
            "bookingadmin",
            "amap",
            "booking",
            "event",
            "loan",
            "raffle",
            "vote",
            name="topic",
        ),
        existing_nullable=False,
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
