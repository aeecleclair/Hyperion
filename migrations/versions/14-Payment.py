"""Payment

Create Date: 2024-05-16 14:59:58.316135
"""

from collections.abc import Sequence
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pytest_alembic import MigrationContext

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "146039b64c92"
down_revision: str | None = "fce1716123e2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "payment_checkout",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("module", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("hello_asso_checkout_id", sa.String(), nullable=False),
        sa.Column("hello_asso_order_id", sa.String(), nullable=True),
        sa.Column("secret", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "payment_checkout_payment",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("checkout_id", sa.Uuid(), nullable=False),
        sa.Column("paid_amount", sa.Integer(), nullable=False),
        sa.Column("hello_asso_payment_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["checkout_id"], ["payment_checkout.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_payment_checkout_payment_hello_asso_payment_id"),
        "payment_checkout_payment",
        ["hello_asso_payment_id"],
        unique=True,
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(
        op.f("ix_payment_checkout_payment_hello_asso_payment_id"),
        table_name="payment_checkout_payment",
    )
    op.drop_table("payment_checkout_payment")
    op.drop_table("payment_checkout")
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
