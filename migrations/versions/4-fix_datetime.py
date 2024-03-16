"""Fix datetime stored in the database

Revision ID: 99a2c70e4a24
Revises: f17e6182b0a9
Create Date: 2024-03-02 20:23:13.078198

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "99a2c70e4a24"
down_revision: str | None = "f17e6182b0a9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Booking
    upgrade_column("booking", "start")
    upgrade_column("booking", "end")
    upgrade_column("booking", "creation")
    # Advert
    upgrade_column("advert_adverts", "date")
    # Amap
    upgrade_column("amap_order", "ordering_date")
    # Calendar
    upgrade_column("calendar_events", "start")
    upgrade_column("calendar_events", "end")
    # Cinema
    upgrade_column("cinema_session", "start")


def downgrade() -> None:
    pass


def upgrade_column(table, column):
    op.execute(
        f'UPDATE "{table}" SET "{column}" = "{column}"::timestamp AT TIME ZONE \'Europe/Paris\'',
    )
    op.alter_column(table, column, type_=sa.DateTime(timezone=False))
