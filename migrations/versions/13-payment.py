"""empty message

Create Date: 2024-05-15 11:42:13.997787
"""

from collections.abc import Sequence
from typing import TYPE_CHECKING, Union

if TYPE_CHECKING:
    from pytest_alembic import MigrationContext

import sqlalchemy as sa
from alembic import op

from app.types.sqlalchemy import TZDateTime

# revision identifiers, used by Alembic.
revision: str = "b78766673a16"
down_revision: str | None = "e98026d51884"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "payment_checkout",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("module", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("hello_asso_checkout_id", sa.String(), nullable=False),
        sa.Column("hello_asso_order_id", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "payment_checkout_payment",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("paid_amount", sa.Integer(), nullable=False),
        sa.Column("hello_asso_payment_id", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_payment_checkout_payment_hello_asso_payment_id"),
        "payment_checkout_payment",
        ["hello_asso_payment_id"],
        unique=True,
    )


def downgrade() -> None:
    # op.drop_table("payment_checkout_payment")
    # op.drop_table("payment_checkout")
    # op.drop_index(
    #     op.f("ix_payment_checkout_payment_hello_asso_payment_id"),
    #     table_name="payment_checkout_payment",
    # )
    pass


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
