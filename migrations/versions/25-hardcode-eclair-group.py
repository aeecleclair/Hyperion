"""empty message

Create Date: 2024-08-22 09:02:59.887161
"""

from collections.abc import Sequence
from typing import TYPE_CHECKING

from app.core.groups.groups_type import GroupType

if TYPE_CHECKING:
    from pytest_alembic import MigrationContext

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c73c7b821728"
down_revision: str | None = "d24003cffdcd"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    t_group = sa.Table(
        "core_group",
        sa.MetaData(),
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    t_membership = sa.Table(
        "core_membership",
        sa.MetaData(),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("group_id", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
    )

    conn = op.get_bind()
    res = conn.execute(
        sa.select(
            t_group.c.id,
        ).where(t_group.c.name == "eclair"),
    ).fetchall()

    if len(res) == 0:
        return

    old_eclair_id = res[0][0]
    new_eclair_id = GroupType.eclair

    # We don't need to do anything if the group id is already the correct one
    if old_eclair_id == new_eclair_id:
        return

    # As the group id is a foreign key in other tables, we can not update it directly
    # We create a new group with the new id
    conn.execute(
        sa.insert(t_group).values(
            id=new_eclair_id,
            name="new_eclair",
            description="",
        ),
    )

    # We update relationships to use the new group id
    conn.execute(
        t_membership.update()
        .where(t_membership.c.group_id == old_eclair_id)
        .values(group_id=new_eclair_id),
    )

    # We delete the old group
    conn.execute(t_group.delete().where(t_group.c.id == old_eclair_id))

    # We rename the new group
    conn.execute(
        t_group.update().where(t_group.c.id == new_eclair_id).values(name="eclair"),
    )


def downgrade() -> None:
    pass


user_id = "7a3ed1bb-c46c-486e-a439-f77ed5c8a7f9"


def pre_test_upgrade(
    alembic_runner: "MigrationContext",
    alembic_connection: sa.Connection,
) -> None:
    alembic_runner.insert_into(
        "core_user",
        {
            "id": user_id,
            "email": "email@email.fr",
            "password_hash": "password_hash",
            "name": "name",
            "firstname": "firstname",
            "nickname": "nickname",
            "birthday": None,
            "promo": 21,
            "phone": "phone",
            "floor": "Autre",
            "created_on": None,
            "external": False,
        },
    )
    alembic_runner.insert_into(
        "core_group",
        {
            "id": "33cd5e2b-49e6-4d65-a652-474466a5dcde",
            "name": "eclair",
            "description": "",
        },
    )
    alembic_runner.insert_into(
        "core_membership",
        {
            "user_id": "7a3ed1bb-c46c-486e-a439-f77ed5c8a7f9",
            "group_id": "33cd5e2b-49e6-4d65-a652-474466a5dcde",
            "description": "",
        },
    )


def test_upgrade(
    alembic_runner: "MigrationContext",
    alembic_connection: sa.Connection,
) -> None:
    new_eclair_id = GroupType.eclair

    rows = alembic_connection.execute(
        sa.text("SELECT id from core_group WHERE name = 'eclair'"),
    ).fetchall()

    assert len(rows) > 0

    assert rows[0][0] == new_eclair_id

    rows = alembic_connection.execute(
        sa.text(f"SELECT group_id from core_membership WHERE user_id = '{user_id}'"),
    ).fetchall()

    assert len(rows) > 0

    assert rows[0][0] == new_eclair_id
