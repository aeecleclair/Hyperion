"""Fix datetime stored in the database

Revision ID: 99a2c70e4a24
Revises: f17e6182b0a9
Create Date: 2024-03-02 20:23:13.078198

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "99a2c70e4a24"
down_revision: Union[str, None] = "f17e6182b0a9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Booking
    op.execute(generate_sql_request("booking", "start"))
    op.execute(generate_sql_request("booking", "end"))
    op.execute(generate_sql_request("booking", "creation"))
    # Advert
    op.execute(generate_sql_request("advert_adverts", "date"))
    # Amap
    op.execute(generate_sql_request("amap_order", "ordering_date"))
    # Calendar
    op.execute(generate_sql_request("calendar_events", "start"))
    op.execute(generate_sql_request("calendar_events", "end"))
    # Cinema
    op.execute(generate_sql_request("cinema_session", "start"))


def downgrade() -> None:
    pass


def generate_sql_request(table, column) -> str:
    return f'UPDATE "{table}" SET "{column}" = "{column}"::timestamp AT TIME ZONE \'Europe/Paris\''


def generate_downgrade_sql_request(table, column) -> str:
    return (
        f'UPDATE "{table}" SET "{column}" = "{column}"::timestamp AT TIME ZONE timezone'
    )
