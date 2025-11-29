"""45-Flappybird3

Create Date: 2025-11-29 20:03:55.301775
"""

from collections.abc import Sequence
from typing import TYPE_CHECKING, Union

if TYPE_CHECKING:
    from pytest_alembic import MigrationContext

import sqlalchemy as sa
from alembic import op

from app.types.sqlalchemy import TZDateTime

# revision identifiers, used by Alembic.
revision: str = "67919cf7c3f5"
down_revision: str | None = "52ce74575f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_table("flappy-bird_score")


def downgrade() -> None:
    op.create_table(
        "flappy-bird_score",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("value", sa.Integer(), nullable=False),
        sa.Column("creation_time", TZDateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["core_user.id"]),
        sa.PrimaryKeyConstraint("id"),
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
