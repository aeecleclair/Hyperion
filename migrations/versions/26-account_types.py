"""account-types

Create Date: 2024-11-08 14:00:56.598058
"""

import re
from collections.abc import Sequence
from enum import Enum
from typing import TYPE_CHECKING

from app.types.core_data import BaseCoreData

if TYPE_CHECKING:
    from pytest_alembic import MigrationContext

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "53c163acf327"
down_revision: str | None = "c73c7b821728"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


class AccountType(Enum):
    student = "student"
    former_student = "former_student"
    staff = "staff"
    association = "association"
    external = "external"
    demo = "demo"


STUDENT_GROUP_ID = "39691052-2ae5-4e12-99d0-7a9f5f2b0136"
FORMER_STUDENT_GROUP_ID = "ab4c7503-41b3-11ee-8177-089798f1a4a5"
STAFF_GROUP_ID = "703056c4-be9d-475c-aa51-b7fc62a96aaa"
ASSOCIATION_GROUP_ID = "29751438-103c-42f2-b09b-33fbb20758a7"
EXTERNAL_GROUP_ID = "b1cd979e-ecc1-4bd0-bc2b-4dad2ba8cded"
DEMO_GROUP_ID = "ae4d1866-e7d9-4d7f-bee7-e0dda24d8dd8"

DEMO_ID = "9bccbd61-2af3-4bd6-adb7-2a5e48756f66"
ECLAIR_ID = "e68d744f-472f-49e5-896f-662d83be7b9a"

ECL_STAFF_REGEX = r"^[\w\-.]*@(enise\.)?ec-lyon\.fr$"
ECL_STUDENT_REGEX = r"^[\w\-.]*@((etu(-enise)?)|(ecl\d{2}))\.ec-lyon\.fr$"
ECL_FORMER_STUDENT_REGEX = r"^[\w\-.]*@centraliens-lyon\.net$"


class ModuleVisibilityAwareness(BaseCoreData):
    """
    Schema for module visibility awareness
    """

    roots: list[str]


user_t = sa.Table(
    "core_user",
    sa.MetaData(),
    sa.Column("id", sa.String),
    sa.Column("email", sa.String),
    sa.Column("account_type", sa.Enum(AccountType, name="accounttype")),
)
group_t = sa.Table(
    "core_group",
    sa.MetaData(),
    sa.Column("id", sa.String),
    sa.Column("name", sa.String),
)
membership_t = sa.Table(
    "core_membership",
    sa.MetaData(),
    sa.Column("user_id", sa.String),
    sa.Column("group_id", sa.String),
)
module_group_visibility_t = sa.Table(
    "module_group_visibility",
    sa.MetaData(),
    sa.Column("root", sa.String),
    sa.Column("allowed_group_id", sa.String),
)
module_account_type_visibility_t = sa.Table(
    "module_account_type_visibility",
    sa.MetaData(),
    sa.Column("root", sa.String),
    sa.Column("allowed_account_type", sa.Enum(AccountType, name="accounttype")),
)

core_data_t = sa.Table(
    "core_data",
    sa.MetaData(),
    sa.Column("schema", sa.String),
    sa.Column("data", sa.String),
)


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###

    op.rename_table("module_visibility", "module_group_visibility")
    sa.Enum(AccountType, name="accounttype").create(op.get_bind())
    op.create_table(
        "module_account_type_visibility",
        sa.Column("root", sa.String(), nullable=False),
        sa.Column(
            "allowed_account_type",
            postgresql.ENUM(
                AccountType,
                name="accounttype",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("root", "allowed_account_type"),
    )
    op.drop_column("core_user_unconfirmed", "account_type")
    op.drop_column("core_user_unconfirmed", "external")
    op.drop_column("core_user", "external")
    op.add_column(
        "core_user",
        sa.Column(
            "account_type",
            sa.Enum(
                AccountType,
                name="accounttype",
            ),
            nullable=False,
            server_default=AccountType.external.value,
        ),
    )

    conn = op.get_bind()
    conn.execute(
        sa.update(
            user_t,
        )
        .where(
            user_t.c.email.regexp_match(ECL_STUDENT_REGEX),
        )
        .values(
            account_type=AccountType.student,
        ),
    )
    conn.execute(
        sa.update(
            user_t,
        )
        .where(
            user_t.c.email.regexp_match(ECL_FORMER_STUDENT_REGEX),
        )
        .values(
            account_type=AccountType.former_student,
        ),
    )
    conn.execute(
        sa.update(
            user_t,
        )
        .where(
            user_t.c.email.regexp_match(ECL_STAFF_REGEX),
        )
        .values(
            account_type=AccountType.staff,
        ),
    )
    conn.execute(
        sa.update(
            user_t,
        )
        .where(user_t.c.id == DEMO_ID)
        .values(
            account_type=AccountType.demo,
        ),
    )
    conn.execute(
        sa.update(
            user_t,
        )
        .where(user_t.c.id == ECLAIR_ID)
        .values(
            account_type=AccountType.association,
        ),
    )

    conn.execute(
        sa.delete(
            membership_t,
        ).where(
            (membership_t.c.group_id == STUDENT_GROUP_ID)
            | (membership_t.c.group_id == FORMER_STUDENT_GROUP_ID)
            | (membership_t.c.group_id == STAFF_GROUP_ID)
            | (membership_t.c.group_id == ASSOCIATION_GROUP_ID)
            | (membership_t.c.group_id == DEMO_GROUP_ID)
            | (membership_t.c.group_id == EXTERNAL_GROUP_ID),
        ),
    )
    group_visibilities = conn.execute(
        sa.select(
            module_group_visibility_t,
        ),
    )
    group_to_account_type = {
        STUDENT_GROUP_ID: AccountType.student,
        FORMER_STUDENT_GROUP_ID: AccountType.former_student,
        STAFF_GROUP_ID: AccountType.staff,
        ASSOCIATION_GROUP_ID: AccountType.association,
        DEMO_GROUP_ID: AccountType.demo,
        EXTERNAL_GROUP_ID: AccountType.external,
    }

    module_awareness = ModuleVisibilityAwareness(
        roots={group_visibility.root for group_visibility in group_visibilities},
    )

    conn.execute(
        sa.insert(
            core_data_t,
        ).values(
            [
                {
                    "schema": ModuleVisibilityAwareness.__name__,
                    "data": module_awareness.model_dump_json(),
                },
            ],
        ),
    )

    for group_visibility in group_visibilities:
        if group_visibility.allowed_group_id in group_to_account_type:
            conn.execute(
                sa.insert(
                    module_account_type_visibility_t,
                ).values(
                    {
                        "root": group_visibility.root,
                        "allowed_account_type": group_to_account_type[
                            group_visibility.allowed_group_id
                        ],
                    },
                ),
            )

    conn.execute(
        sa.delete(
            module_group_visibility_t,
        ).where(
            (module_group_visibility_t.c.allowed_group_id == STUDENT_GROUP_ID)
            | (module_group_visibility_t.c.allowed_group_id == FORMER_STUDENT_GROUP_ID)
            | (module_group_visibility_t.c.allowed_group_id == STAFF_GROUP_ID)
            | (module_group_visibility_t.c.allowed_group_id == ASSOCIATION_GROUP_ID)
            | (module_group_visibility_t.c.allowed_group_id == DEMO_GROUP_ID)
            | (module_group_visibility_t.c.allowed_group_id == EXTERNAL_GROUP_ID),
        ),
    )

    conn.execute(
        sa.delete(
            group_t,
        ).where(
            (group_t.c.id == STUDENT_GROUP_ID)
            | (group_t.c.id == FORMER_STUDENT_GROUP_ID)
            | (group_t.c.id == STAFF_GROUP_ID)
            | (group_t.c.id == ASSOCIATION_GROUP_ID)
            | (group_t.c.id == DEMO_GROUP_ID)
            | (group_t.c.id == EXTERNAL_GROUP_ID),
        ),
    )

    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "core_user_unconfirmed",
        sa.Column(
            "account_type",
            sa.VARCHAR(),
            server_default="external",
            nullable=True,
        ),
    )
    op.add_column(
        "core_user_unconfirmed",
        sa.Column(
            "external",
            sa.BOOLEAN(),
            server_default=sa.sql.true(),
            nullable=False,
        ),
    )
    op.add_column(
        "core_user",
        sa.Column(
            "external",
            sa.Boolean(),
            server_default=sa.sql.true(),
            nullable=False,
        ),
    )

    user_t2 = sa.Table(
        "core_user",
        sa.MetaData(),
        sa.Column("id", sa.String),
        sa.Column("external", sa.Boolean),
    )

    account_type_to_group = {
        AccountType.student: STUDENT_GROUP_ID,
        AccountType.former_student: FORMER_STUDENT_GROUP_ID,
        AccountType.staff: STAFF_GROUP_ID,
        AccountType.association: ASSOCIATION_GROUP_ID,
        AccountType.demo: DEMO_GROUP_ID,
        AccountType.external: EXTERNAL_GROUP_ID,
    }

    conn = op.get_bind()

    conn.execute(
        sa.insert(
            group_t,
        ).values(
            [
                {"id": STUDENT_GROUP_ID, "name": "student"},
                {"id": FORMER_STUDENT_GROUP_ID, "name": "former_student"},
                {"id": STAFF_GROUP_ID, "name": "staff"},
                {"id": ASSOCIATION_GROUP_ID, "name": "association"},
                {"id": EXTERNAL_GROUP_ID, "name": "external"},
                {"id": DEMO_GROUP_ID, "name": "demo"},
            ],
        ),
    )

    account_visibilities = conn.execute(
        sa.select(
            module_account_type_visibility_t,
        ),
    )

    for account_visibility in account_visibilities:
        conn.execute(
            sa.insert(
                module_group_visibility_t,
            ).values(
                {
                    "root": account_visibility.root,
                    "allowed_group_id": account_type_to_group[
                        account_visibility.allowed_account_type
                    ],
                },
            ),
        )

    def update_user(user_id: str, external: bool) -> None:
        conn.execute(
            sa.update(
                user_t2,
            )
            .where(
                user_t2.c.id == user_id,
            )
            .values(
                {"external": external},
            ),
        )

    def insert_membership(user_id: str, group_id: str) -> None:
        conn.execute(
            sa.insert(
                membership_t,
            ).values(
                {"user_id": user_id, "group_id": group_id},
            ),
        )

    users = conn.execute(
        sa.select(
            user_t2,
        ),
    ).fetchall()

    for user in users:
        if re.match(ECL_STUDENT_REGEX, user.email):
            insert_membership(user.id, STUDENT_GROUP_ID)
            update_user(user.id, False)
        elif re.match(ECL_FORMER_STUDENT_REGEX, user.email):
            insert_membership(user.id, FORMER_STUDENT_GROUP_ID)
            update_user(user.id, False)
        elif re.match(ECL_STAFF_REGEX, user.email):
            insert_membership(user.id, STAFF_GROUP_ID)
            update_user(user.id, False)
        else:
            insert_membership(user.id, EXTERNAL_GROUP_ID)
            update_user(user.id, True)

    demo = conn.execute(
        sa.select(
            user_t2,
        ).where(
            user_t2.c.id == DEMO_ID,
        ),
    ).fetchone()
    if demo is not None:
        insert_membership(DEMO_ID, DEMO_GROUP_ID)
        update_user(DEMO_ID, False)

    eclair = conn.execute(
        sa.select(
            user_t2,
        ).where(
            user_t2.c.id == ECLAIR_ID,
        ),
    ).fetchone()
    if eclair is not None:
        insert_membership(ECLAIR_ID, ASSOCIATION_GROUP_ID)
        update_user(ECLAIR_ID, False)

    op.rename_table("module_group_visibility", "module_visibility")
    op.drop_table("module_account_type_visibility")
    op.drop_column("core_user", "account_type")
    sa.Enum(AccountType, name="accounttype").drop(
        op.get_bind(),
    )
    # ### end Alembic commands ###


def pre_test_upgrade(
    alembic_runner: "MigrationContext",
    alembic_connection: sa.Connection,
) -> None:
    alembic_runner.insert_into(
        "core_group",
        {
            "id": DEMO_GROUP_ID,
            "name": "demo",
        },
    )
    alembic_runner.insert_into(
        "core_group",
        {
            "id": STUDENT_GROUP_ID,
            "name": "student",
        },
    )
    alembic_runner.insert_into(
        "core_group",
        {
            "id": FORMER_STUDENT_GROUP_ID,
            "name": "former_student",
        },
    )
    alembic_runner.insert_into(
        "core_group",
        {
            "id": STAFF_GROUP_ID,
            "name": "staff",
        },
    )
    alembic_runner.insert_into(
        "core_group",
        {
            "id": ASSOCIATION_GROUP_ID,
            "name": "association",
        },
    )
    alembic_runner.insert_into(
        "core_group",
        {
            "id": EXTERNAL_GROUP_ID,
            "name": "external",
        },
    )

    alembic_runner.insert_into(
        "core_user",
        {
            "id": DEMO_ID,
            "email": "demo@myecl.fr",
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
        "core_membership",
        {
            "user_id": DEMO_ID,
            "group_id": DEMO_GROUP_ID,
        },
    )
    alembic_runner.insert_into(
        "core_user",
        {
            "id": "5c5f9fdd-bedd-449b-91a3-f3437b95e36b",
            "email": "test@etu.ec-lyon.fr",
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
        "core_membership",
        {
            "user_id": "5c5f9fdd-bedd-449b-91a3-f3437b95e36b",
            "group_id": STUDENT_GROUP_ID,
        },
    )
    alembic_runner.insert_into(
        "core_user",
        {
            "id": "3d565333-aae1-4d70-a645-e6a3bc3ac198",
            "email": "test@etu-enise.ec-lyon.fr",
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
        "core_membership",
        {
            "user_id": "3d565333-aae1-4d70-a645-e6a3bc3ac198",
            "group_id": EXTERNAL_GROUP_ID,
        },
    )
    alembic_runner.insert_into(
        "core_user",
        {
            "id": "1dd04834-700d-4960-ba68-2beab1fa8663",
            "email": "test2@gmail.com",
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
        "core_membership",
        {
            "user_id": "1dd04834-700d-4960-ba68-2beab1fa8663",
            "group_id": EXTERNAL_GROUP_ID,
        },
    )
    alembic_runner.insert_into(
        "core_user",
        {
            "id": ECLAIR_ID,
            "email": "eclair@myecl.fr",
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
        "core_membership",
        {
            "user_id": ECLAIR_ID,
            "group_id": ASSOCIATION_GROUP_ID,
        },
    )
    alembic_runner.insert_into(
        "core_user",
        {
            "id": "64b83ef5-4e13-4827-9f4f-ab4ce1244f4c",
            "email": "test2@ec-lyon.fr",
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
        "core_membership",
        {
            "user_id": "64b83ef5-4e13-4827-9f4f-ab4ce1244f4c",
            "group_id": STAFF_GROUP_ID,
        },
    )
    alembic_runner.insert_into(
        "core_user",
        {
            "id": "f1265ac3-d3cc-4ce5-97f5-82d25b5063f2",
            "email": "test2@enise.ec-lyon.fr",
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
        "core_membership",
        {
            "user_id": "f1265ac3-d3cc-4ce5-97f5-82d25b5063f2",
            "group_id": STAFF_GROUP_ID,
        },
    )
    alembic_runner.insert_into(
        "core_user",
        {
            "id": "b059f348-3678-4d7f-a90e-b1663d60de37",
            "email": "test2@centraliens-lyon.net",
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
        "core_membership",
        {
            "user_id": "b059f348-3678-4d7f-a90e-b1663d60de37",
            "group_id": FORMER_STUDENT_GROUP_ID,
        },
    )


def test_upgrade(
    alembic_runner: "MigrationContext",
    alembic_connection: sa.Connection,
) -> None:
    users = alembic_connection.execute(
        sa.text("SELECT id, account_type from core_user"),
    ).fetchall()

    duos = {
        "1dd04834-700d-4960-ba68-2beab1fa8663": "external",
        "3d565333-aae1-4d70-a645-e6a3bc3ac198": "student",
        "5c5f9fdd-bedd-449b-91a3-f3437b95e36b": "student",
        "64b83ef5-4e13-4827-9f4f-ab4ce1244f4c": "staff",
        "f1265ac3-d3cc-4ce5-97f5-82d25b5063f2": "staff",
        "b059f348-3678-4d7f-a90e-b1663d60de37": "former_student",
        DEMO_ID: "demo",
        ECLAIR_ID: "association",
    }

    for row in users:
        account = duos.get(row[0])
        if account is not None:
            assert row[1] == account

    groups = alembic_connection.execute(
        sa.text("SELECT id from core_group"),
    ).fetchall()

    group_ids = {
        STUDENT_GROUP_ID,
        FORMER_STUDENT_GROUP_ID,
        STAFF_GROUP_ID,
        ASSOCIATION_GROUP_ID,
        EXTERNAL_GROUP_ID,
        DEMO_GROUP_ID,
    }

    for group_id in group_ids:
        assert (group_id,) not in groups
