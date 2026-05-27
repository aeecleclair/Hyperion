"""empty message

Create Date: 2025-07-26 18:06:00.966810
"""

from collections.abc import Sequence
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pytest_alembic import MigrationContext

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "12ceba87cf"
down_revision: str | None = "67919cf7c3f5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "competition_pompom_podium",
        sa.Column("edition_id", sa.Uuid(), nullable=False),
        sa.Column("school_id", sa.Uuid(), nullable=False),
        sa.Column("points", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["edition_id"],
            ["competition_edition.id"],
        ),
        sa.ForeignKeyConstraint(
            ["school_id"],
            ["competition_school_extension.school_id"],
        ),
        sa.PrimaryKeyConstraint("edition_id", "school_id"),
    )
    op.alter_column("competition_product_variant", "school_type", nullable=True)
    op.drop_column("competition_user", "is_volunteer")
    op.drop_constraint(
        "fk_volunteer_registration_user",
        "competition_volunteer_registration",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_volunteer_registration_user",
        "competition_volunteer_registration",
        "core_user",
        ["user_id"],
        ["id"],
    )
    op.add_column(
        "competition_volunteer_shift",
        sa.Column("manager_id", sa.String(), nullable=True),
    )
    op.create_foreign_key(
        "fk_volunteer_shift_manager",
        "competition_volunteer_shift",
        "core_user",
        ["manager_id"],
        ["id"],
    )
    conn = op.get_bind()
    user = conn.execute(
        sa.text("SELECT id FROM core_user LIMIT 1"),
    ).first()
    if user is not None:
        conn.execute(
            sa.text(
                "UPDATE competition_volunteer_shift SET manager_id = :sid",
            ).bindparams(sid=user[0]),
        )
    op.alter_column(
        "competition_volunteer_shift",
        "manager_id",
        nullable=False,
    )
    op.add_column(
        "competition_user",
        sa.Column(
            "allow_pictures",
            sa.Boolean(),
            nullable=True,
        ),
    )
    conn.execute(
        sa.text(
            "UPDATE competition_user SET allow_pictures = true",
        ),
    )
    op.alter_column(
        "competition_user",
        "allow_pictures",
        nullable=False,
    )

    # ### end Alembic commands ###s


def downgrade() -> None:
    op.drop_column("competition_user", "allow_pictures")
    op.drop_constraint(
        "fk_volunteer_shift_manager",
        "competition_volunteer_shift",
        type_="foreignkey",
    )
    op.drop_column("competition_volunteer_shift", "manager_id")
    op.drop_constraint(
        "fk_volunteer_registration_user",
        "competition_volunteer_registration",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_volunteer_registration_user",
        "competition_volunteer_registration",
        "core_user",
        ["user_id"],
        ["id"],
    )
    op.add_column(
        "competition_user",
        sa.Column("is_volunteer", sa.Boolean(), nullable=False),
    )
    op.alter_column("competition_product_variant", "school_type", nullable=False)
    op.drop_table("competition_pompom_podium")


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
