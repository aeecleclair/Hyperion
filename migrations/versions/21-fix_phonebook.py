"""fix-phonebook

Revision ID: 6df7fb89081d
Revises: e3d06397960d
Create Date: 2024-04-11 00:44:52.049956

"""

from collections.abc import Sequence
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pytest_alembic import MigrationContext

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "6df7fb89081d"
down_revision: str | None = "7336e674441f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


class Kinds(Enum):
    comity = "Comité"
    section_ae = "Section AE"
    club_ae = "Club AE"
    section_use = "Section USE"
    club_use = "Club USE"
    association_independant = "Asso indé"


class RoleTags(Enum):
    president = "Prez'"
    sg = "SG"
    treso = "Trez'"
    resp_co = "Respo Com'"
    resp_part = "Respo Partenariats"


def define_order_of_memberships(memberships: list[sa.Row[Any]]) -> list[list]:
    """
    Use tag systeme to introduce a coherent member_order to older membership
    """
    member_order = [tag.value for tag in RoleTags]
    member_order.append("Default")
    memberships2: list[list[Any]] = []
    for membership in memberships:
        if membership[2]:
            tags = membership[2].split(";")
            tags.sort(key=lambda x: member_order.index(x))
        else:
            tags = ["Default"]
        memberships2.append(
            [
                membership[0],
                membership[1],
                tags,
                membership[3],
            ],
        )
    memberships2.sort(
        key=lambda x: (
            min([member_order.index(tag) for tag in x[2]]),
            len(x[2]),
            x[1],
        ),
    )
    return memberships2


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "phonebook_association_associated_groups",
        sa.Column("association_id", sa.String(), nullable=False),
        sa.Column("group_id", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(
            ["association_id"],
            ["phonebook_association.id"],
        ),
        sa.ForeignKeyConstraint(
            ["group_id"],
            ["core_group.id"],
        ),
        sa.PrimaryKeyConstraint("association_id", "group_id"),
    )
    op.add_column(
        "phonebook_membership",
        sa.Column("member_order", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "phonebook_association",
        sa.Column("deactivated", sa.Boolean(), nullable=False, server_default="false"),
    )

    t_association = sa.Table(
        "phonebook_association",
        sa.MetaData(),
        sa.Column("id", sa.String()),
        sa.Column("name", sa.String()),
        sa.Column("kind", sa.Enum(Kinds)),
        sa.Column("mandate_year", sa.Integer()),
        sa.Column("deactivated", sa.Boolean()),
    )

    t_membership = sa.Table(
        "phonebook_membership",
        sa.MetaData(),
        sa.Column("id", sa.String()),
        sa.Column("association_id", sa.String()),
        sa.Column("mandate_year", sa.Integer()),
        sa.Column("role_name", sa.String()),
        sa.Column("role_tags", sa.String()),
        sa.Column("member_order", sa.Integer()),
    )

    conn = op.get_bind()
    res = conn.execute(
        sa.select(
            t_association.c.id,
        ),
    ).fetchall()
    for (id_,) in res:
        memberships = conn.execute(
            sa.select(
                t_membership.c.id,
                t_membership.c.role_name,
                t_membership.c.role_tags,
                t_membership.c.mandate_year,
            ).where(
                t_membership.c.association_id == id_,
            ),
        ).fetchall()
        years = {m[3] for m in memberships}
        for year in years:
            memberships_year = [m for m in memberships if m[3] == year]
            sorted_memberships_year = define_order_of_memberships(memberships_year)
            for i, m in enumerate(sorted_memberships_year):
                conn.execute(
                    t_membership.update()
                    .where(t_membership.c.id == m[0])
                    .values(member_order=i),
                )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("phonebook_membership", "member_order")
    op.drop_column("phonebook_association", "deactivated")
    op.drop_table("phonebook_association_associated_groups")
    # ### end Alembic commands ###


def pre_test_upgrade(
    alembic_runner: "MigrationContext",
    alembic_connection: sa.Connection,
) -> None:
    alembic_runner.insert_into(
        "core_user",
        {
            "id": "11",
            "firstname": "firstname",
            "password_hash": "password",
            "name": "name",
            "email": "email1",
        },
    )
    alembic_runner.insert_into(
        "core_user",
        {
            "id": "12",
            "firstname": "firstname",
            "password_hash": "password",
            "name": "name",
            "email": "email2",
        },
    )
    alembic_runner.insert_into(
        "core_user",
        {
            "id": "13",
            "firstname": "firstname",
            "password_hash": "password",
            "name": "name",
            "email": "email3",
        },
    )
    alembic_runner.insert_into(
        "core_user",
        {
            "id": "14",
            "firstname": "firstname",
            "password_hash": "password",
            "name": "name",
            "email": "email4",
        },
    )
    alembic_runner.insert_into(
        "core_user",
        {
            "id": "15",
            "firstname": "firstname",
            "password_hash": "password",
            "name": "name",
            "email": "email5",
        },
    )

    alembic_runner.insert_into(
        "phonebook_association",
        {
            "id": "9",
            "name": "name",
            "kind": "comity",
            "mandate_year": 2024,
        },
    )
    alembic_runner.insert_into(
        "phonebook_association",
        {
            "id": "10",
            "name": "name",
            "kind": "comity",
            "mandate_year": 2024,
        },
    )
    alembic_runner.insert_into(
        "phonebook_membership",
        {
            "id": "1",
            "user_id": "11",
            "association_id": "9",
            "mandate_year": 2024,
            "role_name": "role_name",
            "role_tags": "Prez'",
        },
    )
    alembic_runner.insert_into(
        "phonebook_membership",
        {
            "id": "2",
            "user_id": "12",
            "association_id": "9",
            "mandate_year": 2024,
            "role_name": "role_name",
            "role_tags": "Respo Com'",
        },
    )
    alembic_runner.insert_into(
        "phonebook_membership",
        {
            "id": "3",
            "user_id": "13",
            "association_id": "9",
            "mandate_year": 2024,
            "role_name": "role_name",
            "role_tags": "SG",
        },
    )
    alembic_runner.insert_into(
        "phonebook_membership",
        {
            "id": "4",
            "user_id": "14",
            "association_id": "9",
            "mandate_year": 2024,
            "role_name": "role_name",
            "role_tags": "Trez'",
        },
    )
    alembic_runner.insert_into(
        "phonebook_membership",
        {
            "id": "5",
            "user_id": "15",
            "association_id": "9",
            "mandate_year": 2024,
            "role_name": "role_name",
            "role_tags": "",
        },
    )
    alembic_runner.insert_into(
        "phonebook_membership",
        {
            "id": "6",
            "user_id": "14",
            "association_id": "10",
            "mandate_year": 2024,
            "role_name": "role_name",
            "role_tags": "Prez';Trez'",
        },
    )
    alembic_runner.insert_into(
        "phonebook_membership",
        {
            "id": "7",
            "user_id": "12",
            "association_id": "10",
            "mandate_year": 2024,
            "role_name": "role_name",
            "role_tags": "",
        },
    )


def test_upgrade(
    alembic_runner: "MigrationContext",
    alembic_connection: sa.Connection,
) -> None:
    # The following lines fails because migrations test are not working
    # The migration does work as expected, it was tested manually

    rows = alembic_connection.execute(
        sa.text("SELECT id, member_order from phonebook_membership"),
    ).fetchall()

    solutions = [
        ("1", 0),
        ("2", 3),
        ("3", 1),
        ("4", 2),
        ("5", 4),
        ("6", 0),
        ("7", 1),
    ]

    for row in rows:
        assert row in solutions
