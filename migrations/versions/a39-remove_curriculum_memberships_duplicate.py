"""remove curriculum memberships duplicate

Create Date: 2025-09-01 11:47:32.727885
"""

from collections.abc import Sequence
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pytest_alembic import MigrationContext

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2880c583d7f1"
down_revision: str | None = "06c94803745b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade():
    op.drop_constraint(
        "cdr_curriculum_membership_pkey",
        table_name="cdr_curriculum_membership",
        type_="primary",
    )

    op.execute("""
        DELETE FROM cdr_curriculum_membership AS c
        WHERE EXISTS (
            SELECT 1
            FROM cdr_curriculum_membership AS sub
            WHERE sub.user_id = c.user_id
            AND sub.curriculum_id < c.curriculum_id
    );
    """)

    op.create_primary_key(
        "cdr_curriculum_membership_pkey",
        "cdr_curriculum_membership",
        ["user_id"],
    )


def downgrade():
    op.drop_constraint(
        "cdr_curriculum_membership_pkey",
        table_name="cdr_curriculum_membership",
        type_="primary",
    )

    op.create_primary_key(
        "cdr_curriculum_membership_pkey",
        "cdr_curriculum_membership",
        ["user_id", "curriculum_id"],
    )


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
