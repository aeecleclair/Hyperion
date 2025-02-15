"""empty message

Create Date: 2024-04-27 17:31:29.082701
"""

from collections.abc import Sequence
from typing import TYPE_CHECKING

import sqlalchemy as sa
from alembic import op

if TYPE_CHECKING:
    from pytest_alembic import MigrationContext

# revision identifiers, used by Alembic.
revision: str = "c3acc9b8dd98"
down_revision: str | None = "d99516f0bbcb"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # We previously did not allow external users to be created
    # thus we can assume that all existing users are not external and set the default value to false
    op.add_column(
        "core_user",
        sa.Column(
            "external",
            sa.Boolean(),
            nullable=False,
            server_default=sa.sql.false(),
        ),
    )
    op.add_column(
        "core_user_unconfirmed",
        sa.Column(
            "external",
            sa.Boolean(),
            nullable=False,
            server_default=sa.sql.false(),
        ),
    )
    op.alter_column(
        "core_user",
        "floor",
        existing_type=sa.Enum(
            "Autre",
            "Adoma",
            "Exte",
            "T1",
            "T2",
            "T3",
            "T4",
            "T56",
            "U1",
            "U2",
            "U3",
            "U4",
            "U56",
            "V1",
            "V2",
            "V3",
            "V45",
            "V6",
            "X1",
            "X2",
            "X3",
            "X4",
            "X5",
            "X6",
            name="floorstype",
        ),
        nullable=True,
    )


def downgrade() -> None:
    op.drop_column("core_user_unconfirmed", "external")
    op.drop_column("core_user", "external")

    core_user = sa.sql.table("core_user", sa.Column("floor"))
    op.execute(
        core_user.update().where(core_user.c.floor.is_(None)).values(floor="Autre"),
    )

    op.alter_column(
        "core_user",
        "floor",
        existing_type=sa.Enum(
            "Autre",
            "Adoma",
            "Exte",
            "T1",
            "T2",
            "T3",
            "T4",
            "T56",
            "U1",
            "U2",
            "U3",
            "U4",
            "U56",
            "V1",
            "V2",
            "V3",
            "V45",
            "V6",
            "X1",
            "X2",
            "X3",
            "X4",
            "X5",
            "X6",
            name="floorstype",
        ),
        # We make this column non nullable, we must provide a default value
        nullable=False,
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
