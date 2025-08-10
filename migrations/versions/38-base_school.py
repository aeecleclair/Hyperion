"""empty message

Create Date: 2025-07-30 11:44:33.566860
"""

from collections.abc import Sequence
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pytest_alembic import MigrationContext

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "5a034ba207dd"
down_revision: str | None = "e81453aa7341"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

school_table = sa.Table(
    "core_school",
    sa.MetaData(),
    sa.Column("id", sa.Uuid(), nullable=False),
    sa.Column("name", sa.String(), nullable=False),
    sa.Column("email_regex", sa.String(), nullable=False),
)


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.update(
            school_table,
        )
        .where(
            school_table.c.id == "d9772da7-1142-4002-8b86-b694b431dfed",
        )
        .values(
            {"name": "base_school"},
        ),
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.update(
            school_table,
        )
        .where(
            school_table.c.id == "d9772da7-1142-4002-8b86-b694b431dfed",
        )
        .values(
            {"name": "centrale_lyon"},
        ),
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
    schools = alembic_connection.execute(
        sa.text(
            "SELECT name FROM core_school WHERE id = 'd9772da7-1142-4002-8b86-b694b431dfed'",
        ),
    ).all()
    assert len(schools) == 1
    assert schools[0][0] == "base_school"
