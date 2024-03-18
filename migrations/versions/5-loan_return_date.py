"""Add a returned date to the loan table

Revision ID: 2fcadbe2f0ad
Revises: f17e6182b0a9
Create Date: 2024-03-01 23:33:20.431056

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2fcadbe2f0ad"
down_revision: str | None = "3f9843f165e9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Schema migration
    op.add_column("loan", sa.Column("returned_date", sa.Date(), nullable=True))

    # Data migration
    t_loan = sa.Table(
        "loan",
        sa.MetaData(),
        sa.Column("id", sa.String()),
        sa.Column("end", sa.Date()),
        sa.Column("returned", sa.Boolean()),
        sa.Column("returned_date", sa.Date()),
    )

    conn = op.get_bind()
    res = conn.execute(
        sa.select(t_loan.c.id, t_loan.c.end).where(t_loan.c.returned),
    ).fetchall()
    for id_, end_ in res:
        conn.execute(
            t_loan.update().where(t_loan.c.id == id_).values(returned_date=end_),
        )


def downgrade() -> None:
    # Schema migration
    op.drop_column("loan", "returned_date")
