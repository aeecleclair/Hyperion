"""Notifications 'create_on' migration

Revision ID: e3d06397960d
Revises: 2fcadbe2f0ad
Create Date: 2024-03-17 19:19:14.297195

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e3d06397960d"
down_revision: str | None = "2fcadbe2f0ad"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "notification_message",
        "expire_on",
        existing_type=sa.DATE(),
        type_=sa.DateTime(timezone=False),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "notification_message",
        "expire_on",
        existing_type=sa.DateTime(timezone=False),
        type_=sa.DATE(),
        existing_nullable=False,
    )
