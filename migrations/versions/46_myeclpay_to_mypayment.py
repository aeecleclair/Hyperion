"""MyECLPay to MyPayment

Create Date: 2025-11-29 22:50:53.781596
"""

from collections.abc import Sequence
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pytest_alembic import MigrationContext

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "467ad07734c0"
down_revision: str | None = "91fadc90f892"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.rename_table(
        "myeclpay_wallet",
        "mypayment_wallet",
    )
    op.rename_table(
        "myeclpay_wallet_device",
        "mypayment_wallet_device",
    )
    op.rename_table(
        "myeclpay_transaction",
        "mypayment_transaction",
    )
    op.rename_table(
        "myeclpay_refund",
        "mypayment_refund",
    )
    op.rename_table(
        "myeclpay_structure",
        "mypayment_structure",
    )
    op.rename_table(
        "myeclpay_structure_manager_transfer",
        "mypayment_structure_manager_transfer",
    )
    op.rename_table(
        "myeclpay_store",
        "mypayment_store",
    )
    op.rename_table(
        "myeclpay_request",
        "mypayment_request",
    )
    op.rename_table("myeclpay_transfer", "mypayment_transfer")
    op.rename_table(
        "myeclpay_seller",
        "mypayment_seller",
    )
    op.rename_table(
        "myeclpay_user_payment",
        "mypayment_user_payment",
    )
    op.rename_table(
        "myeclpay_used_qrcode",
        "mypayment_used_qrcode",
    )
    op.rename_table(
        "myeclpay_invoice",
        "mypayment_invoice",
    )
    op.rename_table(
        "myeclpay_invoice_detail",
        "mypayment_invoice_detail",
    )
    op.rename_table(
        "myeclpay_withdrawal",
        "mypayment_withdrawal",
    )
    # ### end Alembic commands ###s


def downgrade() -> None:
    op.rename_table(
        "mypayment_wallet",
        "myeclpay_wallet",
    )
    op.rename_table(
        "mypayment_wallet_device",
        "myeclpay_wallet_device",
    )
    op.rename_table(
        "mypayment_transaction",
        "myeclpay_transaction",
    )
    op.rename_table(
        "mypayment_refund",
        "myeclpay_refund",
    )
    op.rename_table(
        "mypayment_structure",
        "myeclpay_structure",
    )
    op.rename_table(
        "mypayment_structure_manager_transfer",
        "myeclpay_structure_manager_transfer",
    )
    op.rename_table(
        "mypayment_store",
        "myeclpay_store",
    )
    op.rename_table(
        "mypayment_request",
        "myeclpay_request",
    )
    op.rename_table("mypayment_transfer", "myeclpay_transfer")
    op.rename_table(
        "mypayment_seller",
        "myeclpay_seller",
    )
    op.rename_table(
        "mypayment_user_payment",
        "myeclpay_user_payment",
    )
    op.rename_table(
        "mypayment_used_qrcode",
        "myeclpay_used_qrcode",
    )
    op.rename_table(
        "mypayment_invoice",
        "myeclpay_invoice",
    )
    op.rename_table(
        "mypayment_invoice_detail",
        "myeclpay_invoice_detail",
    )
    op.rename_table(
        "mypayment_withdrawal",
        "myeclpay_withdrawal",
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
