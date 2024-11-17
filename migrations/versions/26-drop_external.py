"""account-types

Create Date: 2024-11-08 14:00:56.598058
"""

import re
from collections.abc import Sequence
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pytest_alembic import MigrationContext

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "53c163acf327"
down_revision: str | None = "c73c7b821728"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DEMO_ID = "9bccbd61-2af3-4bd6-adb7-2a5e48756f66"
ECLAIR_ID = "e68d744f-472f-49e5-896f-662d83be7b9a"

ECL_STAFF_REGEX = r"^[\w\-.]*@(enise\.)?ec-lyon\.fr$"
ECL_STUDENT_REGEX = r"^[\w\-.]*@etu(-enise)?\.ec-lyon\.fr$"
ECL_FORMER_STUDENT_REGEX = r"^[\w\-.]*@centraliens-lyon\.net$"


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("core_user", "external")
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "core_user",
        sa.Column(
            "external",
            sa.Boolean(),
            server_default=sa.text("1"),
            nullable=False,
        ),
    )
    conn = op.get_bind()

    user_t = sa.Table(
        "core_user",
        sa.MetaData(),
        sa.Column("id", sa.String),
        sa.Column("external", sa.Boolean),
    )
    users = conn.execute(
        sa.select(
            user_t,
        ),
    ).fetchall()

    def update_user(user_id: str, external: bool) -> None:
        conn.execute(
            sa.update(
                user_t,
            )
            .where(
                user_t.c.id == user_id,
            )
            .values(
                {"external": external},
            ),
        )

    for user in users:
        if (
            re.match(ECL_STUDENT_REGEX, user.email)
            or re.match(ECL_FORMER_STUDENT_REGEX, user.email)
            or re.match(ECL_STAFF_REGEX, user.email)
        ):
            update_user(user.id, False)
        else:
            update_user(user.id, True)

    update_user(DEMO_ID, False)
    update_user(ECLAIR_ID, False)
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
