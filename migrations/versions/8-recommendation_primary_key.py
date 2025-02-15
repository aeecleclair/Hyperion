"""change primary key type from string to UUID

Create Date: 2024-04-21 02:08:19.548067
"""

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID

import sqlalchemy as sa
from alembic import op

if TYPE_CHECKING:
    from pytest_alembic import MigrationContext

# revision identifiers, used by Alembic.
revision: str = "d99516f0bbcb"
down_revision: str | None = "e3d06397960d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "recommendation",
        "id",
        type_=sa.types.Uuid(),
        postgresql_using="id::uuid",
    )


def downgrade() -> None:
    op.alter_column(
        "recommendation",
        "id",
        type_=sa.types.String(),
    )


def pre_test_upgrade(
    alembic_runner: "MigrationContext",
    alembic_connection: sa.Connection,
) -> None:
    alembic_runner.insert_into(
        "recommendation",
        {
            "id": "66c363bc-c71f-4eae-8376-c37712a312f6",
            "creation": datetime.now(UTC),
            "title": "title",
            "summary": "summary",
            "description": "description",
        },
    )


def test_upgrade(
    alembic_runner: "MigrationContext",
    alembic_connection: sa.Connection,
) -> None:
    rows = alembic_connection.execute(
        sa.text("SELECT id from recommendation"),
    ).fetchall()

    assert len(rows) > 0

    if isinstance(rows[0][0], UUID):
        assert (UUID("66c363bc-c71f-4eae-8376-c37712a312f6"),) in rows
    else:
        # SQLite does not support UUID and will use strings
        assert ("66c363bc-c71f-4eae-8376-c37712a312f6",) in rows
