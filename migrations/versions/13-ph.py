"""10-ph

Create Date: 2024-05-08 13:02:15.712830
"""

from collections.abc import Sequence
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pytest_alembic import MigrationContext

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "fce1716123e2"
down_revision: str | None = "e98026d51884"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ph_papers",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("release_date", sa.Date(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_ph_papers_id"), "ph_papers", ["id"], unique=False)

    op.alter_column(
        "notification_topic_membership",
        "topic",
        existing_type=sa.VARCHAR(length=23),
        type_=sa.Enum(
            "cinema",
            "advert",
            "amap",
            "booking",
            "event",
            "loan",
            "raffle",
            "vote",
            "ph",
            name="topic",
        ),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_ph_papers_id"), table_name="ph_papers")
    op.drop_table("ph_papers")
    op.alter_column(
        "notification_topic_membership",
        "topic",
        existing_type=sa.VARCHAR(length=23),
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
