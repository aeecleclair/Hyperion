"""booking enhancements

Revision ID: 28aa5ef44bf3
Revises:
Create Date: 2023-12-18 00:35:59.678336

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "28aa5ef44bf3"
down_revision = "f20685c9761e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Schema migration
    op.add_column(
        "booking",
        sa.Column(
            "creation",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # Data migration
    t_booking = sa.Table(
        "booking",
        sa.MetaData(),
        sa.Column("id", sa.String()),
        sa.Column("start", sa.DateTime()),
        sa.Column("end", sa.DateTime()),
        sa.Column("recurrence_rule", sa.String()),
    )

    conn = op.get_bind()
    res = conn.execute(
        sa.select(t_booking.c.id, t_booking.c.start, t_booking.c.end).where(
            t_booking.c.recurrence_rule != "",
        ),
    ).fetchall()
    for id_, booking_start, booking_end in res:
        endBooking = booking_end.replace(
            year=booking_start.year,
            month=booking_start.month,
            day=booking_start.day,
        )
        endBooking = endBooking.astimezone().replace(tzinfo=None)
        conn.execute(
            t_booking.update().where(t_booking.c.id == id_).values(end=endBooking),
        )


def downgrade() -> None:
    # Schema migration
    op.drop_column("booking", "creation")
