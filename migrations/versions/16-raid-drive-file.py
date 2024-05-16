"""empty message

Revision ID: 0534d0f07976
Revises: 4a02570cc225
Create Date: 2024-04-27 12:25:18.883339

"""

from collections.abc import Sequence
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pytest_alembic import MigrationContext

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0534d0f07976"
down_revision: str | None = "4a02570cc225"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column("raid_team", sa.Column("file_id", sa.String(), nullable=True))
    op.add_column(
        "raid_security_file",
        sa.Column("emergency_person_firstname", sa.String(), nullable=True),
    )
    op.add_column(
        "raid_security_file",
        sa.Column("emergency_person_name", sa.String(), nullable=True),
    )
    op.add_column(
        "raid_security_file",
        sa.Column("emergency_person_phone", sa.String(), nullable=True),
    )
    with op.batch_alter_table("recommendation") as batch_op:
        batch_op.alter_column(
            column_name="id",
            existing_type=sa.VARCHAR(),
            type_=sa.Uuid(),
            existing_nullable=False,
        )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("raid_team", "file_id")

    with op.batch_alter_table("recommendation") as batch_op:
        batch_op.alter_column(
            column_name="id",
            existing_type=sa.Uuid(),
            type_=sa.VARCHAR(),
            existing_nullable=False,
        )
    op.drop_column("raid_security_file", "emergency_person_phone")
    op.drop_column("raid_security_file", "emergency_person_name")
    op.drop_column("raid_security_file", "emergency_person_firstname")
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
