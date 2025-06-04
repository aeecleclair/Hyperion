from datetime import datetime
from uuid import UUID

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.memberships import models_memberships
from app.core.myeclpay.types_myeclpay import (
    RequestStatus,
    TransactionStatus,
    TransactionType,
    TransferType,
    WalletDeviceStatus,
    WalletType,
)
from app.core.users import models_users
from app.types.sqlalchemy import Base, PrimaryKey


class Wallet(Base):
    __tablename__ = "myeclpay_wallet"

    id: Mapped[PrimaryKey]
    type: Mapped[WalletType]
    balance: Mapped[int]  # Stored in cents

    store: Mapped["Store | None"] = relationship(init=False, lazy="joined")
    user: Mapped[models_users.CoreUser | None] = relationship(
        init=False,
        secondary="myeclpay_user_payment",
        lazy="joined",
    )


class WalletDevice(Base):
    __tablename__ = "myeclpay_wallet_device"

    id: Mapped[PrimaryKey]
    name: Mapped[str]
    wallet_id: Mapped[UUID] = mapped_column(ForeignKey("myeclpay_wallet.id"))
    ed25519_public_key: Mapped[bytes] = mapped_column(unique=True)
    creation: Mapped[datetime]
    status: Mapped[WalletDeviceStatus]
    activation_token: Mapped[str] = mapped_column(unique=True)


class Transaction(Base):
    __tablename__ = "myeclpay_transaction"

    id: Mapped[PrimaryKey]
    debited_wallet_id: Mapped[UUID] = mapped_column(ForeignKey("myeclpay_wallet.id"))
    debited_wallet_device_id: Mapped[UUID] = mapped_column(
        ForeignKey("myeclpay_wallet_device.id"),
    )
    credited_wallet_id: Mapped[UUID] = mapped_column(ForeignKey("myeclpay_wallet.id"))
    transaction_type: Mapped[TransactionType]

    # User that scanned the qr code
    # Will be None if the transaction is a request
    seller_user_id: Mapped[str | None] = mapped_column(ForeignKey("core_user.id"))

    total: Mapped[int]  # Stored in cents
    creation: Mapped[datetime]
    status: Mapped[TransactionStatus]

    # The Seller may add a note to the transaction, for example to specify the product that was buyed
    store_note: Mapped[str | None]

    qr_code_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("myeclpay_used_qrcode.qr_code_id"),
    )

    debited_wallet: Mapped[Wallet] = relationship(
        init=False,
        foreign_keys=[debited_wallet_id],
    )
    credited_wallet: Mapped[Wallet] = relationship(
        init=False,
        foreign_keys=[credited_wallet_id],
    )

    refund: Mapped["Refund | None"] = relationship(
        init=False,
        back_populates="transaction",
        uselist=False,  # We expect only one refund per transaction
        lazy="joined",
    )


class Refund(Base):
    __tablename__ = "myeclpay_refund"

    id: Mapped[PrimaryKey]
    transaction_id: Mapped[UUID] = mapped_column(
        ForeignKey("myeclpay_transaction.id"),
        unique=True,
    )
    debited_wallet_id: Mapped[UUID] = mapped_column(ForeignKey("myeclpay_wallet.id"))
    credited_wallet_id: Mapped[UUID] = mapped_column(ForeignKey("myeclpay_wallet.id"))
    total: Mapped[int]  # Stored in cents
    creation: Mapped[datetime]
    seller_user_id: Mapped[str | None] = mapped_column(ForeignKey("core_user.id"))

    transaction: Mapped[Transaction] = relationship(
        init=False,
        back_populates="refund",
        lazy="joined",
    )
    debited_wallet: Mapped[Wallet] = relationship(
        init=False,
        foreign_keys=[debited_wallet_id],
    )
    credited_wallet: Mapped[Wallet] = relationship(
        init=False,
        foreign_keys=[credited_wallet_id],
    )


class Structure(Base):
    __tablename__ = "myeclpay_structure"

    id: Mapped[PrimaryKey]
    name: Mapped[str] = mapped_column(unique=True)
    manager_user_id: Mapped[str] = mapped_column(ForeignKey("core_user.id"))
    association_membership_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("core_association_membership.id"),
        default=None,
    )

    manager_user: Mapped[models_users.CoreUser] = relationship(
        init=False,
        lazy="joined",
    )
    association_membership: Mapped[
        models_memberships.CoreAssociationMembership | None
    ] = relationship(init=False, lazy="joined")


class StructureManagerTransfert(Base):
    __tablename__ = "myeclpay_structure_manager_transfer"

    structure_id: Mapped[UUID] = mapped_column(
        ForeignKey("myeclpay_structure.id"),
        primary_key=True,
    )
    user_id: Mapped[str] = mapped_column(ForeignKey("core_user.id"))
    confirmation_token: Mapped[str] = mapped_column(unique=True)
    valid_until: Mapped[datetime]


class Store(Base):
    __tablename__ = "myeclpay_store"

    id: Mapped[PrimaryKey]
    name: Mapped[str] = mapped_column(unique=True)
    structure_id: Mapped[UUID] = mapped_column(ForeignKey("myeclpay_structure.id"))

    wallet_id: Mapped[UUID] = mapped_column(
        ForeignKey("myeclpay_wallet.id"),
        unique=True,
    )

    structure: Mapped[Structure] = relationship(init=False, lazy="joined")


class Request(Base):
    __tablename__ = "myeclpay_request"

    id: Mapped[PrimaryKey]
    wallet_id: Mapped[str] = mapped_column(ForeignKey("myeclpay_wallet.id"))
    creation: Mapped[datetime]
    total: Mapped[int]  # Stored in cents
    store_id: Mapped[str] = mapped_column(ForeignKey("myeclpay_store.id"))
    name: Mapped[str]
    store_note: Mapped[str | None]
    callback: Mapped[str]
    status: Mapped[RequestStatus]
    transaction_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("myeclpay_transaction.id"),
        unique=True,
    )


class Transfer(Base):
    __tablename__ = "myeclpay_transfer"

    id: Mapped[PrimaryKey]
    type: Mapped[TransferType]
    transfer_identifier: Mapped[str]

    # TODO remove if we only accept hello asso
    approver_user_id: Mapped[str | None] = mapped_column(ForeignKey("core_user.id"))

    wallet_id: Mapped[UUID] = mapped_column(ForeignKey("myeclpay_wallet.id"))
    total: Mapped[int]  # Stored in cents
    creation: Mapped[datetime]
    confirmed: Mapped[bool]


class Seller(Base):
    __tablename__ = "myeclpay_seller"

    user_id: Mapped[str] = mapped_column(
        ForeignKey("core_user.id"),
        primary_key=True,
    )
    store_id: Mapped[UUID] = mapped_column(
        ForeignKey("myeclpay_store.id"),
        primary_key=True,
    )
    can_bank: Mapped[bool]
    can_see_history: Mapped[bool]
    can_cancel: Mapped[bool]
    can_manage_sellers: Mapped[bool]

    user: Mapped[models_users.CoreUser] = relationship(init=False, lazy="joined")


class UserPayment(Base):
    __tablename__ = "myeclpay_user_payment"

    user_id: Mapped[str] = mapped_column(
        ForeignKey("core_user.id"),
        primary_key=True,
    )
    wallet_id: Mapped[UUID] = mapped_column(
        ForeignKey("myeclpay_wallet.id"),
        unique=True,
    )
    accepted_tos_signature: Mapped[datetime]
    accepted_tos_version: Mapped[int]


class UsedQRCode(Base):
    __tablename__ = "myeclpay_used_qrcode"

    qr_code_id: Mapped[PrimaryKey]
    qr_code_tot: Mapped[int | None]
    qr_code_iat: Mapped[datetime | None]
    qr_code_key: Mapped[UUID | None]
    qr_code_store: Mapped[bool | None]
    signature: Mapped[str | None]
