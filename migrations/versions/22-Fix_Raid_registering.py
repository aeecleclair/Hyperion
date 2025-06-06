"""empty message

Create Date: 2024-08-29 16:26:38.681239
"""

from collections.abc import Sequence
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pytest_alembic import MigrationContext

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "1e86c328ae8f"
down_revision: str | None = "6df7fb89081d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column(
        "raid_participant",
        "bike_size",
        existing_type=sa.VARCHAR(length=2),
        type_=sa.Enum("XS", "S", "M", "L", "XL", "None_", name="size"),
        existing_nullable=True,
    )
    op.alter_column(
        "raid_participant",
        "t_shirt_size",
        existing_type=sa.VARCHAR(length=2),
        type_=sa.Enum("XS", "S", "M", "L", "XL", "None_", name="size"),
        existing_nullable=True,
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column(
        "raid_participant",
        "t_shirt_size",
        existing_type=sa.Enum("XS", "S", "M", "L", "XL", name="size"),
        type_=sa.VARCHAR(length=2),
        existing_nullable=True,
    )
    op.alter_column(
        "raid_participant",
        "bike_size",
        existing_type=sa.Enum("XS", "S", "M", "L", "XL", name="size"),
        type_=sa.VARCHAR(length=2),
        existing_nullable=True,
    )
    # ### end Alembic commands ###


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
