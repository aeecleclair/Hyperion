"""schools

Create Date: 2024-10-26 19:04:51.089828
"""

import enum
from collections.abc import Sequence
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pytest_alembic import MigrationContext

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1e6e8b52103"
down_revision: str | None = "53c163acf327"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

centrale_regex = r"^[\w\-.]*@(etu(-enise)?\.)?ec-lyon\.fr$"


class AccountType(enum.Enum):
    student = "student"
    former_student = "former_student"
    staff = "staff"
    association = "association"
    external = "external"
    demo = "demo"


class AccountType2(enum.Enum):
    student = "student"
    former_student = "former_student"
    staff = "staff"
    association = "association"
    external = "external"
    other_school_student = "other_school_student"
    demo = "demo"


DEMO_ID = "9bccbd61-2af3-4bd6-adb7-2a5e48756f66"
ECLAIR_ID = "e68d744f-472f-49e5-896f-662d83be7b9a"

ECL_STAFF_REGEX = r"^[\w\-.]*@(enise\.)?ec-lyon\.fr$"
ECL_STUDENT_REGEX = r"^[\w\-.]*@((etu(-enise)?)|(ecl\d{2}))\.ec-lyon\.fr$"
ECL_FORMER_STUDENT_REGEX = r"^[\w\-.]*@centraliens-lyon\.net$"

school_table = sa.Table(
    "core_school",
    sa.MetaData(),
    sa.Column("id", sa.Uuid(), nullable=False),
    sa.Column("name", sa.String(), nullable=False),
    sa.Column("email_regex", sa.String(), nullable=False),
)
user_table = sa.Table(
    "core_user",
    sa.MetaData(),
    sa.Column("id", sa.String(), nullable=False),
    sa.Column("email", sa.String(), nullable=False),
    sa.Column("account_type", sa.Enum(AccountType, name="accounttype"), nullable=False),
    sa.Column("school_id", sa.Uuid(), nullable=False),
)

visibility_table = sa.Table(
    "module_account_type_visibility",
    sa.MetaData(),
    sa.Column("root", sa.String(), nullable=False),
    sa.Column(
        "allowed_account_type",
        sa.Enum(AccountType, name="accounttype"),
        nullable=False,
    ),
)


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "core_school",
        sa.Column("id", sa.Uuid(), nullable=False, index=True),
        sa.Column("name", sa.String(), nullable=False, index=True, unique=True),
        sa.Column("email_regex", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    conn = op.get_bind()

    conn.execute(
        sa.insert(school_table).values(
            id="dce19aa2-8863-4c93-861e-fb7be8f610ed",
            name="no_school",
            email_regex=".*",
        ),
    )

    users = conn.execute(
        sa.select(user_table.c.id, user_table.c.account_type),
    ).fetchall()

    visibilities = conn.execute(
        sa.select(visibility_table.c.root, visibility_table.c.allowed_account_type),
    ).fetchall()

    with op.batch_alter_table("core_user") as batch_op:
        batch_op.add_column(
            sa.Column(
                "school_id",
                sa.Uuid(),
                nullable=False,
                server_default="dce19aa2-8863-4c93-861e-fb7be8f610ed",
            ),
        )
        batch_op.create_foreign_key(
            "core_user_school_id",
            "core_school",
            ["school_id"],
            ["id"],
        )
        batch_op.drop_column("account_type")

    op.drop_table("module_account_type_visibility")

    sa.Enum(AccountType, name="accounttype").drop(
        conn,
    )

    op.create_table(
        "module_account_type_visibility",
        sa.Column("root", sa.String(), nullable=False),
        sa.Column(
            "allowed_account_type",
            sa.Enum(
                AccountType2,
                name="accounttype",
            ),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("root", "allowed_account_type"),
    )

    with op.batch_alter_table("core_user") as batch_op:
        batch_op.add_column(
            sa.Column(
                "account_type",
                sa.Enum(AccountType2, name="accounttype"),
                nullable=False,
                server_default="external",
            ),
        )

    conn.execute(
        sa.insert(school_table).values(
            id="d9772da7-1142-4002-8b86-b694b431dfed",
            name="Centrale Lyon",
            email_regex=centrale_regex,
        ),
    )

    for user in users:
        conn.execute(
            sa.update(user_table)
            .where(user_table.c.id == user.id)
            .values(
                account_type=user.account_type,
                school_id="d9772da7-1142-4002-8b86-b694b431dfed"
                if user.account_type != AccountType.external
                else "dce19aa2-8863-4c93-861e-fb7be8f610ed",
            ),
        )

    for visibility in visibilities:
        conn.execute(
            sa.insert(visibility_table).values(
                root=visibility.root,
                allowed_account_type=visibility.allowed_account_type,
            ),
        )

    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###

    conn = op.get_bind()

    users = conn.execute(
        sa.select(user_table.c.id, user_table.c.account_type),
    ).fetchall()

    visibilities = conn.execute(
        sa.select(visibility_table.c.root, visibility_table.c.allowed_account_type),
    ).fetchall()

    with op.batch_alter_table("core_user") as batch_op:
        batch_op.drop_constraint("core_user_school_id", type_="foreignkey")
        batch_op.drop_column("school_id")
        batch_op.drop_column("account_type")

    op.drop_table("module_account_type_visibility")

    sa.Enum(AccountType2, name="accounttype").drop(
        op.get_bind(),
    )

    op.create_table(
        "module_account_type_visibility",
        sa.Column("root", sa.String(), nullable=False),
        sa.Column(
            "allowed_account_type",
            sa.Enum(AccountType, name="accounttype"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("root", "allowed_account_type"),
    )

    with op.batch_alter_table("core_user") as batch_op:
        batch_op.add_column(
            sa.Column(
                "account_type",
                sa.Enum(AccountType, name="accounttype"),
                nullable=False,
                server_default="external",
            ),
        )

    op.drop_index(op.f("ix_core_school_name"), table_name="core_school")
    op.drop_index(op.f("ix_core_school_id"), table_name="core_school")
    op.drop_table("core_school")

    for user in users:
        conn.execute(
            sa.update(user_table)
            .where(user_table.c.id == user.id)
            .values(
                account_type=user.account_type
                if user.account_type != AccountType2.other_school_student
                else AccountType.external,
            ),
        )

    for visibility in visibilities:
        conn.execute(
            sa.insert(visibility_table).values(
                root=visibility.root,
                allowed_account_type=visibility.allowed_account_type,
            ),
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
