"""Notifications 'create_on' migration

Revision ID: e3d06397960d
Revises: 6afc765adaa2
Create Date: 2024-03-17 19:19:14.297195

"""

from collections.abc import Sequence
from typing import TYPE_CHECKING

import sqlalchemy as sa
from alembic import op

if TYPE_CHECKING:
    from pytest_alembic import MigrationContext

# revision identifiers, used by Alembic.
revision: str = "e3d06397960d"
down_revision: str | None = "17b92dc4b50d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        table_name="notification_message",
        column_name="expire_on",
        type_=sa.DateTime(timezone=False),
    )


def downgrade() -> None:
    op.alter_column(
        table_name="notification_message",
        column_name="expire_on",
        type_=sa.Date(),
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
