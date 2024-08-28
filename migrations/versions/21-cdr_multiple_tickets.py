"""cdr-multiple-tickets

Create Date: 2024-08-26 21:33:44.790403
"""

from collections.abc import Sequence
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pytest_alembic import MigrationContext

import sqlalchemy as sa
from alembic import op

from app.types.sqlalchemy import TZDateTime

# revision identifiers, used by Alembic.
revision: str = "bccdd745730c"
down_revision: str | None = "7336e674441f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "cdr_ticket_generator",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("max_use", sa.Integer(), nullable=False),
        sa.Column("expiration", TZDateTime(), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["cdr_product.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.execute(
        "INSERT INTO cdr_ticket_generator (product_id, name, max_use, expiration) SELECT id, name_fr, ticket_max_use, ticket_expiration FROM cdr_product WHERE generate_ticket==True",
    )
    op.drop_column("cdr_product", "ticket_expiration")
    op.drop_column("cdr_product", "generate_ticket")
    op.drop_column("cdr_product", "ticket_max_use")
    op.add_column("cdr_ticket", sa.Column("generator_id", sa.Uuid(), nullable=True))
    op.create_unique_constraint("ticket_secret_unique", "cdr_ticket", ["secret"])
    op.create_foreign_key(
        "ticket_generator",
        "cdr_ticket",
        "cdr_ticket_generator",
        ["generator_id"],
        ["id"],
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint("ticket_generator", "cdr_ticket", type_="foreignkey")
    op.drop_constraint("ticket_secret_unique", "cdr_ticket", type_="unique")
    op.drop_column("cdr_ticket", "generator_id")
    op.add_column(
        "cdr_product",
        sa.Column("ticket_max_use", sa.Integer(), nullable=True),
    )
    op.add_column(
        "cdr_product",
        sa.Column("generate_ticket", sa.Boolean(), nullable=False),
    )
    op.add_column(
        "cdr_product",
        sa.Column("ticket_expiration", TZDateTime(), nullable=True),
    )
    op.drop_table("cdr_ticket_generator")
    # ### end Alembic commands ###


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
