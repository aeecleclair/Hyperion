"""account-types

Create Date: 2024-11-08 14:00:56.598058
"""

import re
from collections.abc import Sequence
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pytest_alembic import MigrationContext

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "53c163acf327"
down_revision: str | None = "d24003cffdcd"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


class AccountType(Enum):
    student = "student"
    formerstudent = "formerstudent"
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
ECL_STUDENT_REGEX = r"^[\w\-.]*@etu(-enise)?\.ec-lyon\.fr$"
ECL_FORMER_STUDENT_REGEX = r"^[\w\-.]*@centraliens-lyon\.net$"

user_t = sa.Table(
    "core_user",
    sa.MetaData(),
    sa.Column("email", sa.String),
    sa.Column("account_type", sa.Enum(AccountType, name="account_type")),
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


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.rename_table("module_visibility", "module_group_visibility")
    op.create_table(
        "module_account_type_visibility",
        sa.Column("root", sa.String(), nullable=False),
        sa.Column(
            "allowed_account_type",
            sa.Enum(AccountType, name="account_type"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("root", "allowed_account_type"),
    )
    op.drop_column("core_user", "external")
    op.add_column(
        "core_user",
        sa.Column(
            "account_type",
            sa.Enum(
                AccountType,
                name="account_type",
            ),
            nullable=False,
            server_default=sa.text(AccountType.external.value),
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
            account_type=AccountType.formerstudent,
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
    op.rename_table("module_group_visibility", "module_visibility")
    op.drop_table("module_account_type_visibility")
    op.add_column(
        "core_user",
        sa.Column(
            "external",
            sa.Boolean(),
            server_default=sa.text("1"),
            nullable=False,
        ),
    )
    op.drop_column("core_user", "account_type")
    conn = op.get_bind()
    conn.execute(
        sa.insert(
            group_t,
        ).values(
            [
                {"id": STUDENT_GROUP_ID, "name": "student"},
                {"id": FORMER_STUDENT_GROUP_ID, "name": "formerstudent"},
                {"id": STAFF_GROUP_ID, "name": "staff"},
                {"id": ASSOCIATION_GROUP_ID, "name": "sssociation"},
                {"id": EXTERNAL_GROUP_ID, "name": "external"},
                {"id": DEMO_GROUP_ID, "name": "demo"},
            ],
        ),
    )
    user_t2 = sa.Table(
        "core_user",
        sa.MetaData(),
        sa.Column("id", sa.String),
        sa.Column("external", sa.Boolean),
    )
    users = conn.execute(
        sa.select(
            user_t2,
        ),
    ).fetchall()

    def insert_membership(user_id: str, group_id: str) -> None:
        conn.execute(
            sa.insert(
                membership_t,
            ).values(
                {"user_id": user_id, "group_id": group_id},
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

    insert_membership(DEMO_ID, DEMO_GROUP_ID)
    update_user(DEMO_ID, False)
    insert_membership(ECLAIR_ID, ASSOCIATION_GROUP_ID)
    update_user(ECLAIR_ID, False)

    sa.Enum(AccountType, name="account_type").drop(
        op.get_bind(),
    )
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
