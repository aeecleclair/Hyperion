"""Allow to mark users as external users during email migration

Create Date: 2024-08-21 13:03:35.258072
"""

from collections.abc import Sequence
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pytest_alembic import MigrationContext

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7faf06d2a5fe"
down_revision: str | None = "bcb330b5cbec"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "core_user_email_migration_code",
        sa.Column(
            "make_user_external",
            sa.Boolean(),
            nullable=False,
            server_default=sa.sql.false(),
        ),
    )


def downgrade() -> None:
    op.drop_column("core_user_email_migration_code", "make_user_external")


def pre_test_upgrade(
    alembic_runner: "MigrationContext",
    alembic_connection: sa.Connection,
) -> None:
    alembic_runner.insert_into(
        "core_user",
        {
            "id": "63bc3d6b-9fff-4da1-80ad-7996f6ad3513",
            "email": "email",
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
        "core_user_email_migration_code",
        {
            "user_id": "63bc3d6b-9fff-4da1-80ad-7996f6ad3513",
            "new_email": "new_email",
            "old_email": "old_email",
            "confirmation_token": "token",
        },
    )


def test_upgrade(
    alembic_runner: "MigrationContext",
    alembic_connection: sa.Connection,
) -> None:
    rows = alembic_connection.execute(
        sa.text("SELECT make_user_external from core_user_email_migration_code"),
    ).fetchall()

    assert len(rows) > 0

    # Old users should not be external users
    assert not rows[0][0]
