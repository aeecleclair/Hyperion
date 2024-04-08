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
    def upgrade_column_with_wrong_datetime(table, column):
        update_column_with_wrong_datetime(table, column, False)

    def upgrade_column_type(table, column):
        update_column_type(table, column, False)

    # Booking
    upgrade_column_with_wrong_datetime("booking", "start")
    upgrade_column_with_wrong_datetime("booking", "end")
    upgrade_column_with_wrong_datetime("booking", "creation")
    # Advert
    upgrade_column_with_wrong_datetime("advert_adverts", "date")
    # Amap
    upgrade_column_with_wrong_datetime("amap_order", "ordering_date")
    # Calendar
    upgrade_column_with_wrong_datetime("calendar_events", "start")
    upgrade_column_with_wrong_datetime("calendar_events", "end")
    # Cinema
    upgrade_column_with_wrong_datetime("cinema_session", "start")

    # Core
    upgrade_column_type("refresh_token", "revoked_on")
    upgrade_column_type("refresh_token", "expire_on")
    upgrade_column_type("refresh_token", "created_on")
    upgrade_column_type("notification_message", "delivery_datetime")
    upgrade_column_type("core_user_unconfirmed", "expire_on")
    upgrade_column_type("core_user_unconfirmed", "created_on")
    upgrade_column_type("core_user_recover_request", "expire_on")
    upgrade_column_type("core_user_recover_request", "created_on")
    upgrade_column_type("core_user", "created_on")
    upgrade_column_type("authorization_code", "expire_on")


def downgrade() -> None:
    def downgrade_column_with_wrong_datetime(table, column):
        update_column_with_wrong_datetime(table, column, True)

    def downgrade_column_type(table, column):
        update_column_type(table, column, True)

    # Booking
    downgrade_column_with_wrong_datetime("booking", "start")
    downgrade_column_with_wrong_datetime("booking", "end")
    downgrade_column_with_wrong_datetime("booking", "creation")
    # Advert
    downgrade_column_with_wrong_datetime("advert_adverts", "date")
    # Amap
    downgrade_column_with_wrong_datetime("amap_order", "ordering_date")
    # Calendar
    downgrade_column_with_wrong_datetime("calendar_events", "start")
    downgrade_column_with_wrong_datetime("calendar_events", "end")
    # Cinema
    downgrade_column_with_wrong_datetime("cinema_session", "start")

    # Core
    downgrade_column_type("refresh_token", "revoked_on")
    downgrade_column_type("refresh_token", "expire_on")
    downgrade_column_type("refresh_token", "created_on")
    downgrade_column_type("notification_message", "delivery_datetime")
    downgrade_column_type("core_user_unconfirmed", "expire_on")
    downgrade_column_type("core_user_unconfirmed", "created_on")
    downgrade_column_type("core_user_recover_request", "expire_on")
    downgrade_column_type("core_user_recover_request", "created_on")
    downgrade_column_type("core_user", "created_on")
    downgrade_column_type("authorization_code", "expire_on")


# See https://www.postgresql.org/docs/11/functions-datetime.html#FUNCTIONS-DATETIME-ZONECONVERT understand how AT TIME ZONE works in PostgreSQL


def update_column_with_wrong_datetime(table, column, is_downgrade):
    op.alter_column(
        table,
        column,
        type_=sa.DateTime(timezone=is_downgrade),
        postgresql_using=f"\"{column}\" AT TIME ZONE 'Etc/UTC' AT TIME ZONE 'Europe/Paris' AT TIME ZONE 'Etc/UTC'",
    )


def update_column_type(table, column, is_downgrade):
    op.alter_column(
        table,
        column,
        type_=sa.DateTime(timezone=is_downgrade),
        postgresql_using=f"\"{column}\" AT TIME ZONE 'Etc/UTC'",
    )
