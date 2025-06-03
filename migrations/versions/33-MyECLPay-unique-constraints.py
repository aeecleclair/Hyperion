"""empty message

Create Date: 2025-05-29 17:32:45.619972
"""

from collections.abc import Sequence
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pytest_alembic import MigrationContext

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ea26eebe3f8d"
down_revision: str | None = "e16b58cc6084"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_unique_constraint(
        "myeclpay_refund_transaction_id_key",
        "myeclpay_refund",
        ["transaction_id"],
    )
    op.create_unique_constraint(
        "myeclpay_request_transaction_id_key",
        "myeclpay_request",
        ["transaction_id"],
    )
    op.create_unique_constraint(
        "myeclpay_structure_manager_transfer_confirmation_token_key",
        "myeclpay_structure_manager_transfer",
        ["confirmation_token"],
    )
    op.create_unique_constraint(
        "myeclpay_wallet_device_ed25519_public_key_key",
        "myeclpay_wallet_device",
        ["ed25519_public_key"],
    )


def downgrade() -> None:
    op.drop_constraint(
        constraint_name="myeclpay_refund_transaction_id_key",
        table_name="myeclpay_refund",
        type_="unique",
    )
    op.drop_constraint(
        constraint_name="myeclpay_request_transaction_id_key",
        table_name="myeclpay_request",
        type_="unique",
    )
    op.drop_constraint(
        constraint_name="myeclpay_structure_manager_transfer_confirmation_token_key",
        table_name="myeclpay_structure_manager_transfer",
        type_="unique",
    )
    op.drop_constraint(
        constraint_name="myeclpay_wallet_device_ed25519_public_key_key",
        table_name="myeclpay_wallet_device",
        type_="unique",
    )


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
