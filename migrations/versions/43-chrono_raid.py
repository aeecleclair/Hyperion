"""29-chrono_raid

Create Date: 2025-03-20 14:25:49.975112
"""

from collections.abc import Sequence
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pytest_alembic import MigrationContext

import sqlalchemy as sa
from alembic import op

from app.types.sqlalchemy import TZDateTime

# revision identifiers, used by Alembic.
revision: str = "118c4f75ebda"
down_revision: str | None = "c4812e1ab108"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "chrono_raid_data",
        sa.Column("filename", sa.String(), nullable=False),
        sa.Column("content", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("filename"),
    )
    op.create_index(
        op.f("ix_chrono_raid_data_filename"),
        "chrono_raid_data",
        ["filename"],
        unique=False,
    )
    op.create_table(
        "chrono_raid_remarks",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("date", TZDateTime(), nullable=False),
        sa.Column("ravito", sa.String(), nullable=False),
        sa.Column("text", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_chrono_raid_remarks_id"),
        "chrono_raid_remarks",
        ["id"],
        unique=False,
    )
    op.create_table(
        "chrono_raid_temps",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("dossard", sa.Integer(), nullable=False),
        sa.Column("date", TZDateTime(), nullable=False),
        sa.Column("parcours", sa.String(), nullable=False),
        sa.Column("ravito", sa.String(), nullable=False),
        sa.Column("status", sa.Boolean(), nullable=False),
        sa.Column("last_modification_date", TZDateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_chrono_raid_temps_id"),
        "chrono_raid_temps",
        ["id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_chrono_raid_temps_id"), table_name="chrono_raid_temps")
    op.drop_table("chrono_raid_temps")

    op.drop_index(op.f("ix_chrono_raid_remarks_id"), table_name="chrono_raid_remarks")
    op.drop_table("chrono_raid_remarks")

    op.drop_table("chrono_raid_data")


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
