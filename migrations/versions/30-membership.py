"""membership

Create Date: 2025-02-02 04:01:15.306205
"""

import uuid
from collections.abc import Sequence
from enum import Enum
from typing import TYPE_CHECKING

from app.core.groups.groups_type import GroupType
from app.core.schools.schools_type import SchoolType

if TYPE_CHECKING:
    from pytest_alembic import MigrationContext

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ea30ad00bb01"
down_revision: str | None = "c73c7f521728"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


class AvailableAssociationMembership(str, Enum):
    aeecl = "AEECL"
    useecl = "USEECL"


group_table = sa.Table(
    "core_group",
    sa.MetaData(),
    sa.Column("id", sa.String(), primary_key=True),
    sa.Column("name", sa.String(), nullable=False),
)

old_user_membership_table = sa.Table(
    "core_association_user_membership",
    sa.MetaData(),
    sa.Column("id", sa.UUID(), primary_key=True),
    sa.Column("membership", sa.Enum(AvailableAssociationMembership), nullable=False),
)

new_user_membership_table = sa.Table(
    "core_association_user_membership",
    sa.MetaData(),
    sa.Column("id", sa.UUID(), primary_key=True),
    sa.Column("association_membership_id", sa.UUID(), nullable=False),
)

association_membership_table = sa.Table(
    "core_association_membership",
    sa.MetaData(),
    sa.Column("id", sa.UUID(), primary_key=True),
    sa.Column("name", sa.String(), nullable=False),
    sa.Column("group_id", sa.String(), nullable=False),
)

old_product_table = sa.Table(
    "cdr_product",
    sa.MetaData(),
    sa.Column("id", sa.String(), primary_key=True),
    sa.Column(
        "related_membership",
        sa.Enum(AvailableAssociationMembership),
        nullable=True,
    ),
)


new_product_table = sa.Table(
    "cdr_product",
    sa.MetaData(),
    sa.Column("id", sa.String(), primary_key=True),
    sa.Column("related_membership_id", sa.UUID(), nullable=True),
)

AEECL_ID = uuid.uuid4()
USEECL_ID = uuid.uuid4()


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    conn = op.get_bind()

    op.rename_table(
        "core_association_membership",
        "core_association_user_membership",
    )
    op.create_table(
        "core_association_membership",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("group_id", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
        sa.ForeignKeyConstraint(
            ["group_id"],
            ["core_group.id"],
        ),
    )
    ids = [group[0] for group in conn.execute(sa.select(group_table)).fetchall()]
    if GroupType.BDE.value not in ids:
        conn.execute(
            sa.insert(
                group_table,
            ).values(
                {"id": GroupType.BDE, "name": "BDE"},
            ),
        )
    if GroupType.BDS.value not in ids:
        conn.execute(
            sa.insert(
                group_table,
            ).values(
                {"id": GroupType.BDS, "name": "BDS"},
            ),
        )

    conn.execute(
        sa.insert(
            association_membership_table,
        ).values(
            [
                {"id": AEECL_ID, "name": "AEECL", "group_id": GroupType.BDE},
                {"id": USEECL_ID, "name": "USEECL", "group_id": GroupType.BDS},
            ],
        ),
    )

    membership_content = conn.execute(sa.select(old_user_membership_table))
    op.drop_index(
        op.f("ix_core_association_membership_membership"),
        table_name="core_association_user_membership",
    )
    with op.batch_alter_table("core_association_user_membership") as batch_op:
        batch_op.drop_column("membership")
        batch_op.add_column(
            sa.Column(
                "association_membership_id",
                sa.Uuid(),
                nullable=False,
                server_default=str(AEECL_ID),
            ),
        )
        batch_op.create_foreign_key(
            "fk_association_membership_id_core_association_membership_id",
            "core_association_membership",
            ["association_membership_id"],
            ["id"],
        )
    for membership in membership_content:
        if membership[1] == AvailableAssociationMembership.useecl:
            conn.execute(
                sa.update(
                    new_user_membership_table,
                )
                .where(
                    new_user_membership_table.c.id == membership[0],
                )
                .values(
                    {"association_membership_id": USEECL_ID},
                ),
            )

    product_content = conn.execute(sa.select(old_product_table))
    with op.batch_alter_table("cdr_product") as batch_op:
        batch_op.add_column(
            sa.Column("related_membership_id", sa.Uuid(), nullable=True),
        )
        batch_op.create_foreign_key(
            "fk_related_membership_id_core_association_membership_id",
            "core_association_membership",
            ["related_membership_id"],
            ["id"],
        )
        batch_op.drop_column("related_membership")

    for product in product_content:
        if product[1] == AvailableAssociationMembership.useecl:
            conn.execute(
                sa.update(
                    new_product_table,
                )
                .where(
                    new_product_table.c.id == product[0],
                )
                .values(
                    {"related_membership_id": USEECL_ID},
                ),
            )
        elif product[1] == AvailableAssociationMembership.aeecl:
            conn.execute(
                sa.update(
                    new_product_table,
                )
                .where(
                    new_product_table.c.id == product[0],
                )
                .values(
                    {"related_membership_id": AEECL_ID},
                ),
            )

    op.create_index(
        op.f("ix_core_association_user_membership_association_membership_id"),
        "core_association_user_membership",
        ["association_membership_id"],
        unique=False,
    )
    sa.Enum(AvailableAssociationMembership).drop(op.get_bind())
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    conn = op.get_bind()

    sa.Enum(AvailableAssociationMembership).create(conn)

    op.drop_index(
        op.f("ix_core_association_user_membership_association_membership_id"),
        table_name="core_association_user_membership",
    )

    product_content = conn.execute(sa.select(new_product_table))
    with op.batch_alter_table("cdr_product") as batch_op:
        batch_op.drop_constraint(
            "fk_related_membership_id_core_association_membership_id",
            type_="foreignkey",
        )
        batch_op.drop_column("related_membership_id")
        batch_op.add_column(
            sa.Column(
                "related_membership",
                sa.Enum(
                    AvailableAssociationMembership,
                    name="availableassociationmembership",
                ),
                nullable=True,
            ),
        )

    for product in product_content:
        if product[1] == USEECL_ID:
            conn.execute(
                sa.update(
                    old_product_table,
                )
                .where(
                    old_product_table.c.id == product[0],
                )
                .values(
                    {"related_membership": AvailableAssociationMembership.useecl},
                ),
            )
        elif product[1] == AEECL_ID:
            conn.execute(
                sa.update(
                    old_product_table,
                )
                .where(
                    old_product_table.c.id == product[0],
                )
                .values(
                    {"related_membership": AvailableAssociationMembership.aeecl},
                ),
            )
    membership_content = conn.execute(sa.select(new_user_membership_table))
    with op.batch_alter_table("core_association_user_membership") as batch_op:
        batch_op.drop_constraint(
            "fk_association_membership_id_core_association_membership_id",
            type_="foreignkey",
        )
        batch_op.drop_column("association_membership_id")
        batch_op.add_column(
            sa.Column(
                "membership",
                sa.Enum(
                    AvailableAssociationMembership,
                    name="availableassociationmembership",
                    extend_existing=True,
                ),
                nullable=False,
                server_default="aeecl",
            ),
        )

    for membership in membership_content:
        if membership[1] == USEECL_ID:
            conn.execute(
                sa.update(
                    old_user_membership_table,
                )
                .where(
                    old_user_membership_table.c.id == membership[0],
                )
                .values(
                    {"membership": AvailableAssociationMembership.useecl},
                ),
            )

    op.drop_table("core_association_membership")
    op.rename_table(
        "core_association_user_membership",
        "core_association_membership",
    )
    op.create_index(
        op.f("ix_core_association_membership_membership"),
        table_name="core_association_membership",
        columns=["membership"],
        unique=False,
    )
    # ### end Alembic commands ###


user_id = str(uuid.uuid4())
membership_id1 = str(uuid.uuid4())
membership_id2 = str(uuid.uuid4())
group_id = str(uuid.uuid4())
seller_id = str(uuid.uuid4())
product_id = str(uuid.uuid4())


def pre_test_upgrade(
    alembic_runner: "MigrationContext",
    alembic_connection: sa.Connection,
) -> None:
    alembic_runner.insert_into(
        "core_user",
        {
            "id": user_id,
            "email": "email546",
            "password_hash": "password_hash",
            "name": "name",
            "firstname": "firstname",
            "nickname": "nickname",
            "birthday": None,
            "promo": 21,
            "phone": None,
            "floor": "Autre",
            "created_on": None,
            "account_type": "student",
            "school_id": SchoolType.no_school.value,
        },
    )
    alembic_runner.insert_into(
        "core_association_membership",
        {
            "id": membership_id1,
            "user_id": user_id,
            "membership": "aeecl",
            "start_date": "2025-02-02",
            "end_date": "2026-02-02",
        },
    )
    alembic_runner.insert_into(
        "core_association_membership",
        {
            "id": membership_id2,
            "user_id": user_id,
            "membership": "useecl",
            "start_date": "2025-02-02",
            "end_date": "2026-02-02",
        },
    )
    alembic_runner.insert_into(
        "core_group",
        {
            "id": group_id,
            "name": "name654",
        },
    )
    alembic_runner.insert_into(
        "cdr_seller",
        {
            "id": seller_id,
            "group_id": group_id,
            "name": "name",
            "order": 1,
        },
    )

    alembic_runner.insert_into(
        "cdr_product",
        {
            "id": product_id,
            "seller_id": seller_id,
            "name_fr": "name_fr",
            "available_online": True,
            "related_membership": "aeecl",
        },
    )


def test_upgrade(
    alembic_runner: "MigrationContext",
    alembic_connection: sa.Connection,
) -> None:
    memberships = alembic_connection.execute(
        sa.text("SELECT * FROM core_association_membership"),
    ).all()
    assert len(memberships) == 2
    assert memberships[0][1] == "AEECL"
    assert memberships[1][1] == "USEECL"

    user_memberships = alembic_connection.execute(
        sa.text("SELECT * FROM core_association_user_membership"),
    ).all()
    assert len(user_memberships) == 2
    assert user_memberships[0][4] == memberships[0][0]
    assert user_memberships[1][4] == memberships[1][0]

    products = alembic_connection.execute(
        sa.text("SELECT * FROM cdr_product"),
    ).all()
    assert len(products) == 1
    assert products[0][7] == memberships[0][0]
