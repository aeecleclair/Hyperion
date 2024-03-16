"""pydantic_v2

Revision ID: f17e6182b0a9
Revises: 28aa5ef44bf3
Create Date: 2024-02-20 19:13:26.528768

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f17e6182b0a9"
down_revision: str | None = "28aa5ef44bf3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "loaner_item",
        "suggested_lending_duration",
        existing_type=sa.Interval(),
        type_=sa.Integer(),
        postgresql_using="extract(EPOCH FROM suggested_lending_duration)",
    )


def downgrade() -> None:
    op.alter_column(
        "loaner_item",
        "suggested_lending_duration",
        existing_type=sa.Integer(),
        type_=sa.Interval(),
        postgresql_using="suggested_lending_duration * INTERVAL '1 second'",
    )
