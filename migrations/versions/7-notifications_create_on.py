"""Notifications 'create_on' migration

Revision ID: e3d06397960d
Revises: 6afc765adaa2
Create Date: 2024-03-17 19:19:14.297195

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e3d06397960d"
down_revision: str | None = "6afc765adaa2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "notification_message",
        "expire_on",
        type_=sa.DateTime(timezone=False),
    )


def downgrade() -> None:
    op.alter_column(
        "notification_message",
        "expire_on",
        type_=sa.Date(),
    )
