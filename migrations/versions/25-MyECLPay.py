"""MyECLPay

Create Date: 2024-10-30 11:24:47.348081
"""

from collections.abc import Sequence
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pytest_alembic import MigrationContext

import sqlalchemy as sa
from alembic import op

from app.types.sqlalchemy import TZDateTime

# revision identifiers, used by Alembic.
revision: str = "e16b58cc6084"
down_revision: str | None = "d24003cffdcd"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "myeclpay_used_qrcode",
        sa.Column("qr_code_id", sa.Uuid(), nullable=False),
        sa.PrimaryKeyConstraint("qr_code_id"),
    )
    op.create_table(
        "myeclpay_wallet",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("type", sa.Enum("USER", "STORE", name="wallettype"), nullable=False),
        sa.Column("balance", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "myeclpay_store",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column(
            "membership",
            sa.Enum("aeecl", "useecl", name="availableassociationmembership"),
            nullable=False,
        ),
        sa.Column("wallet_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["wallet_id"],
            ["myeclpay_wallet.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_table(
        "myeclpay_transfer",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "type",
            sa.Enum(
                "HELLO_ASSO",
                "CHECK",
                "CASH",
                "BANK_TRANSFER",
                name="transfertype",
            ),
            nullable=False,
        ),
        sa.Column("transfer_identifier", sa.String(), nullable=False),
        sa.Column("approver_user_id", sa.String(), nullable=True),
        sa.Column("wallet_id", sa.Uuid(), nullable=False),
        sa.Column("total", sa.Integer(), nullable=False),
        sa.Column("creation", TZDateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["wallet_id"],
            ["myeclpay_wallet.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "myeclpay_user_payment",
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("wallet_id", sa.Uuid(), nullable=False),
        sa.Column("accepted_cgu_signature", TZDateTime(), nullable=False),
        sa.Column("accepted_cgu_version", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["core_user.id"],
        ),
        sa.ForeignKeyConstraint(
            ["wallet_id"],
            ["myeclpay_wallet.id"],
        ),
        sa.PrimaryKeyConstraint("user_id"),
    )
    op.create_table(
        "myeclpay_wallet_device",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("wallet_id", sa.Uuid(), nullable=False),
        sa.Column("ed25519_public_key", sa.LargeBinary(), nullable=False),
        sa.Column("creation", TZDateTime(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("UNACTIVE", "ACTIVE", "DISABLED", name="walletdevicestatus"),
            nullable=False,
        ),
        sa.Column("activation_token", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(
            ["wallet_id"],
            ["myeclpay_wallet.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "myeclpay_seller",
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("store_id", sa.Uuid(), nullable=False),
        sa.Column("can_bank", sa.Boolean(), nullable=False),
        sa.Column("can_see_historic", sa.Boolean(), nullable=False),
        sa.Column("can_cancel", sa.Boolean(), nullable=False),
        sa.Column("can_manage_sellers", sa.Boolean(), nullable=False),
        sa.Column("store_admin", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(
            ["store_id"],
            ["myeclpay_store.id"],
        ),
        sa.PrimaryKeyConstraint("user_id", "store_id"),
    )
    op.create_table(
        "myeclpay_transaction",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("giver_wallet_id", sa.Uuid(), nullable=False),
        sa.Column("giver_wallet_device_id", sa.Uuid(), nullable=False),
        sa.Column("receiver_wallet_id", sa.Uuid(), nullable=False),
        sa.Column(
            "transaction_type",
            sa.Enum("DIRECT", "REQUEST", name="transactiontype"),
            nullable=False,
        ),
        sa.Column("seller_user_id", sa.String(), nullable=True),
        sa.Column("total", sa.Integer(), nullable=False),
        sa.Column("creation", TZDateTime(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("CONFIRMED", "CANCELED", name="transactionstatus"),
            nullable=False,
        ),
        sa.Column("store_note", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(
            ["giver_wallet_device_id"],
            ["myeclpay_wallet_device.id"],
        ),
        sa.ForeignKeyConstraint(
            ["giver_wallet_id"],
            ["myeclpay_wallet.id"],
        ),
        sa.ForeignKeyConstraint(
            ["receiver_wallet_id"],
            ["myeclpay_wallet.id"],
        ),
        sa.ForeignKeyConstraint(
            ["seller_user_id"],
            ["core_user.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "myeclpay_request",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("wallet_id", sa.Uuid(), nullable=False),
        sa.Column("creation", TZDateTime(), nullable=False),
        sa.Column("total", sa.Integer(), nullable=False),
        sa.Column("store_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("store_note", sa.String(), nullable=True),
        sa.Column("callback", sa.String(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("PROPOSED", "ACCEPTED", "REFUSED", name="requeststatus"),
            nullable=False,
        ),
        sa.Column("transaction_id", sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(
            ["store_id"],
            ["myeclpay_store.id"],
        ),
        sa.ForeignKeyConstraint(
            ["transaction_id"],
            ["myeclpay_transaction.id"],
        ),
        sa.ForeignKeyConstraint(
            ["wallet_id"],
            ["myeclpay_wallet.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    op.drop_table("myeclpay_used_qrcode")
    op.drop_table("myeclpay_wallet")
    op.drop_table("myeclpay_store")
    op.drop_table("myeclpay_transfer")
    op.drop_table("myeclpay_user_payment")
    op.drop_table("myeclpay_wallet_device")
    op.drop_table("myeclpay_seller")
    op.drop_table("myeclpay_transaction")
    op.drop_table("myeclpay_request")


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
