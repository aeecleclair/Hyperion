"""empty message

Create Date: 2024-04-27 17:31:29.082701
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

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
    with op.batch_alter_table("core_user") as batch_op:
        batch_op.alter_column(
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

    with op.batch_alter_table("core_user") as batch_op:
        batch_op.alter_column(
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
            nullable=False,
        )
