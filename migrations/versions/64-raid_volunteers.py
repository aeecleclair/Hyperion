"""raid_volunteers

Create Date: 2026-04-21 00:05:00.000000
"""

from collections.abc import Sequence
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pytest_alembic import MigrationContext

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from app.types.sqlalchemy import TZDateTime

# revision identifiers, used by Alembic.
revision: str = "b23c5f9d8a42"
down_revision: str | None = "9e1a4b2d7f10"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # The size enum was created in migration 19-raid_registering; reuse it.
    size = postgresql.ENUM(
        "XS",
        "S",
        "M",
        "L",
        "XL",
        name="size",
        create_type=False,
    )
    op.create_table(
        "raid_volunteer",
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("edition_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", TZDateTime(), nullable=False),
        sa.Column("validated", sa.Boolean(), nullable=False),
        sa.Column("cancelled", sa.Boolean(), nullable=False),
        sa.Column("t_shirt_size", size, nullable=True),
        sa.Column("diet", sa.String(), nullable=True),
        sa.Column("allergy", sa.String(), nullable=True),
        sa.Column("emergency_person_name", sa.String(), nullable=True),
        sa.Column("emergency_person_phone", sa.String(), nullable=True),
        sa.Column(
            "has_car",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column("car_seats", sa.Integer(), nullable=True),
        sa.Column(
            "is_special_driver",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "is_utility_vehicle_driver",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "is_parcours_helper",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["core_user.id"]),
        sa.ForeignKeyConstraint(["edition_id"], ["raid_edition.id"]),
        sa.PrimaryKeyConstraint("user_id", "edition_id"),
    )


def downgrade() -> None:
    op.drop_table("raid_volunteer")


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
