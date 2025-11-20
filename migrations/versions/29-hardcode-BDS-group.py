"""empty message

Create Date: 2024-08-22 09:02:59.887161
"""

from collections.abc import Sequence
from enum import Enum
from typing import TYPE_CHECKING
from uuid import uuid4

from app.core.schools.schools_type import SchoolType

if TYPE_CHECKING:
    from pytest_alembic import MigrationContext

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c73c7f521728"
down_revision: str | None = "c778706af06f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


class GroupType(str, Enum):
    # Core groups
    admin = "0a25cb76-4b63-4fd3-b939-da6d9feabf28"
    AE = "45649735-866a-49df-b04b-a13c74fd5886"

    # Module related groups
    amap = "70db65ee-d533-4f6b-9ffa-a4d70a17b7ef"
    BDE = "53a669d6-84b1-4352-8d7c-421c1fbd9c6a"
    CAA = "6c6d7e88-fdb8-4e42-b2b5-3d3cfd12e7d6"
    cinema = "ce5f36e6-5377-489f-9696-de70e2477300"
    raid_admin = "e9e6e3d3-9f5f-4e9b-8e5f-9f5f4e9b8e5f"
    ph = "4ec5ae77-f955-4309-96a5-19cc3c8be71c"
    admin_cdr = "c1275229-46b2-4e53-a7c4-305513bb1a2a"
    eclair = "1f841bd9-00be-41a7-96e1-860a18a46105"
    BDS = "61af3e52-7ef9-4608-823a-39d51e83d1db"
    seed_library = "09153d2a-14f4-49a4-be57-5d0f265261b9"


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

    t_booking_manager = sa.Table(
        "booking_manager",
        sa.MetaData(),
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("group_id", sa.String(), nullable=False),
    )
    t_cdr_seller = sa.Table(
        "cdr_seller",
        sa.MetaData(),
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("group_id", sa.String(), nullable=False),
        sa.Column("order", sa.Integer(), nullable=False),
    )
    t_phonebook_association_associated_groups = sa.Table(
        "phonebook_association_associated_groups",
        sa.MetaData(),
        sa.Column("association_id", sa.String(), nullable=False),
        sa.Column("group_id", sa.String(), nullable=False),
    )
    t_raffle = sa.Table(
        "raffle",
        sa.MetaData(),
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("group_id", sa.String(), nullable=False),
    )

    conn = op.get_bind()
    res = conn.execute(
        sa.select(
            t_group.c.id,
        ).where(t_group.c.name == "BDS"),
    ).fetchall()

    if len(res) == 0:
        return

    old_BDS_id = res[0][0]
    new_BDS_id = GroupType.BDS

    # We don't need to do anything if the group id is already the correct one
    if old_BDS_id == new_BDS_id:
        return

    # As the group id is a foreign key in other tables, we can not update it directly
    # We create a new group with the new id
    conn.execute(
        sa.insert(t_group).values(
            id=new_BDS_id,
            name="new_BDS",
            description="",
        ),
    )

    # We update relationships to use the new group id
    conn.execute(
        t_membership.update()
        .where(t_membership.c.group_id == old_BDS_id)
        .values(group_id=new_BDS_id),
    )
    conn.execute(
        t_booking_manager.update()
        .where(t_booking_manager.c.group_id == old_BDS_id)
        .values(group_id=new_BDS_id),
    )
    conn.execute(
        t_cdr_seller.update()
        .where(t_cdr_seller.c.group_id == old_BDS_id)
        .values(group_id=new_BDS_id),
    )
    conn.execute(
        t_phonebook_association_associated_groups.update()
        .where(t_phonebook_association_associated_groups.c.group_id == old_BDS_id)
        .values(group_id=new_BDS_id),
    )
    conn.execute(
        t_raffle.update()
        .where(t_raffle.c.group_id == old_BDS_id)
        .values(group_id=new_BDS_id),
    )

    # We delete the old group
    conn.execute(t_group.delete().where(t_group.c.id == old_BDS_id))

    # We rename the new group
    conn.execute(
        t_group.update().where(t_group.c.id == new_BDS_id).values(name="BDS"),
    )


def downgrade() -> None:
    pass


test_user_id = str(uuid4())
test_booking_manager_id = str(uuid4())
test_cdr_seller_id = str(uuid4())
test_phonebook_association_id = str(uuid4())
test_raffle_id = str(uuid4())

test_old_BDS_id = str(uuid4())


def pre_test_upgrade(
    alembic_runner: "MigrationContext",
    alembic_connection: sa.Connection,
) -> None:
    alembic_runner.insert_into(
        "core_user",
        {
            "id": test_user_id,
            "email": "email8465@email.fr",
            "password_hash": "password_hash",
            "name": "name",
            "firstname": "firstname",
            "nickname": "nickname",
            "birthday": None,
            "promo": 21,
            "phone": "phone",
            "floor": "Autre",
            "created_on": None,
            "account_type": "student",
            "school_id": str(SchoolType.no_school.value),
        },
    )
    alembic_runner.insert_into(
        "core_group",
        {
            "id": test_old_BDS_id,
            "name": "BDS",
            "description": "",
        },
    )
    alembic_runner.insert_into(
        "core_membership",
        {
            "user_id": test_user_id,
            "group_id": test_old_BDS_id,
            "description": "",
        },
    )

    alembic_runner.insert_into(
        "booking_manager",
        {
            "id": test_booking_manager_id,
            "name": "TestBookingManager2",
            "group_id": test_old_BDS_id,
        },
    )

    alembic_runner.insert_into(
        "cdr_seller",
        {
            "id": test_cdr_seller_id,
            "name": "TestCDRSeller",
            "group_id": test_old_BDS_id,
            "order": 1,
        },
    )

    alembic_runner.insert_into(
        "phonebook_association",
        {
            "id": test_phonebook_association_id,
            "name": "TestAsso",
            "description": "TestAsso",
            "kind": "club_ae",
            "mandate_year": 2024,
            "deactivated": False,
        },
    )
    alembic_runner.insert_into(
        "phonebook_association_associated_groups",
        {
            "association_id": test_phonebook_association_id,
            "group_id": test_old_BDS_id,
        },
    )
    alembic_runner.insert_into(
        "raffle",
        {
            "id": test_raffle_id,
            "name": "TestRaffle",
            "status": "creation",
            "group_id": test_old_BDS_id,
            "description": "TestRaffle",
        },
    )


def test_upgrade(
    alembic_runner: "MigrationContext",
    alembic_connection: sa.Connection,
) -> None:
    new_BDS_id = GroupType.BDS

    rows = alembic_connection.execute(
        sa.text("SELECT id from core_group WHERE name = 'BDS'"),
    ).fetchall()

    assert len(rows) > 0

    assert rows[0][0] == new_BDS_id

    rows = alembic_connection.execute(
        sa.text(
            f"SELECT group_id from core_membership WHERE user_id = '{test_user_id}'",
        ),
    ).fetchall()

    assert len(rows) > 0

    assert rows[0][0] == new_BDS_id

    rows = alembic_connection.execute(
        sa.text(
            f"SELECT group_id from booking_manager WHERE id = '{test_booking_manager_id}'",
        ),
    ).fetchall()

    assert len(rows) > 0

    assert rows[0][0] == new_BDS_id

    rows = alembic_connection.execute(
        sa.text(
            f"SELECT group_id from cdr_seller WHERE id = '{test_cdr_seller_id}'",
        ),
    ).fetchall()

    assert len(rows) > 0

    assert rows[0][0] == new_BDS_id

    rows = alembic_connection.execute(
        sa.text(
            f"SELECT group_id from phonebook_association_associated_groups WHERE association_id = '{test_phonebook_association_id}'",
        ),
    ).fetchall()

    assert len(rows) > 0

    assert rows[0][0] == new_BDS_id

    rows = alembic_connection.execute(
        sa.text(
            f"SELECT group_id from raffle WHERE id = '{test_raffle_id}'",
        ),
    ).fetchall()

    assert len(rows) > 0

    assert rows[0][0] == new_BDS_id
