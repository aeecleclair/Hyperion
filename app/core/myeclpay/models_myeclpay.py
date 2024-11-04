from datetime import datetime
from uuid import UUID

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, MappedAsDataclass, mapped_column, relationship

from app.core import models_core
from app.core.myeclpay.types_myeclpay import (
    RequestStatus,
    TransactionStatus,
    TransactionType,
    TransferType,
    WalletDeviceStatus,
    WalletType,
)
from app.types.membership import AvailableAssociationMembership
from app.types.sqlalchemy import Base, PrimaryKey


class Wallet(MappedAsDataclass, Base):
    __tablename__ = "myeclpay_wallet"

    id: Mapped[PrimaryKey]
    type: Mapped[WalletType]
    balance: Mapped[int]  # Stored in cents

    store: Mapped["Store | None"] = relationship(init=False, lazy="joined")
    user: Mapped[models_core.CoreUser | None] = relationship(
        init=False,
        secondary="myeclpay_user_payment",
        lazy="joined",
    )


class WalletDevice(MappedAsDataclass, Base):
    __tablename__ = "myeclpay_wallet_device"

    id: Mapped[PrimaryKey]
    name: Mapped[str]
    wallet_id: Mapped[UUID] = mapped_column(ForeignKey("myeclpay_wallet.id"))
    ed25519_public_key: Mapped[bytes]
    creation: Mapped[datetime]
    status: Mapped[WalletDeviceStatus]
    activation_token: Mapped[str] = mapped_column(unique=True)


class Transaction(MappedAsDataclass, Base):
    __tablename__ = "myeclpay_transaction"

    id: Mapped[PrimaryKey]
    giver_wallet_id: Mapped[UUID] = mapped_column(ForeignKey("myeclpay_wallet.id"))
    giver_wallet_device_id: Mapped[UUID] = mapped_column(
        ForeignKey("myeclpay_wallet_device.id"),
    )
    receiver_wallet_id: Mapped[UUID] = mapped_column(ForeignKey("myeclpay_wallet.id"))
    transaction_type: Mapped[TransactionType]

    # User that scanned the qr code
    # Will be None if the transaction is a request
    seller_user_id: Mapped[str | None] = mapped_column(ForeignKey("core_user.id"))

    total: Mapped[int]  # Stored in cents
    creation: Mapped[datetime]
    status: Mapped[TransactionStatus]

    # The Seller may add a note to the transaction, for example to specify the product that was buyed
    store_note: Mapped[str | None]

    giver_wallet: Mapped[Wallet] = relationship(
        init=False,
        foreign_keys=[giver_wallet_id],
    )
    receiver_wallet: Mapped[Wallet] = relationship(
        init=False,
        foreign_keys=[receiver_wallet_id],
    )


class Store(MappedAsDataclass, Base):
    __tablename__ = "myeclpay_store"

    id: Mapped[PrimaryKey]
    name: Mapped[str] = mapped_column(unique=True)

    membership: Mapped[AvailableAssociationMembership]

    wallet_id: Mapped[UUID] = mapped_column(
        ForeignKey("myeclpay_wallet.id"),
        unique=True,
    )


class Request(MappedAsDataclass, Base):
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
    )


class Transfer(MappedAsDataclass, Base):
    __tablename__ = "myeclpay_transfer"

    id: Mapped[PrimaryKey]
    type: Mapped[TransferType]
    transfer_identifier: Mapped[str]

    # TODO remove if we only accept hello asso
    approver_user_id: Mapped[str | None]

    wallet_id: Mapped[UUID] = mapped_column(ForeignKey("myeclpay_wallet.id"))
    total: Mapped[int]  # Stored in cents
    creation: Mapped[datetime]


class Seller(MappedAsDataclass, Base):
    __tablename__ = "myeclpay_seller"

    user_id: Mapped[str] = mapped_column(primary_key=True)
    store_id: Mapped[UUID] = mapped_column(
        ForeignKey("myeclpay_store.id"),
        primary_key=True,
    )
    can_bank: Mapped[bool]
    can_see_historic: Mapped[bool]
    can_cancel: Mapped[bool]
    can_manage_sellers: Mapped[bool]
    store_admin: Mapped[bool]


class UserPayment(MappedAsDataclass, Base):
    __tablename__ = "myeclpay_user_payment"

    user_id: Mapped[str] = mapped_column(ForeignKey("core_user.id"), primary_key=True)
    wallet_id: Mapped[UUID] = mapped_column(
        ForeignKey("myeclpay_wallet.id"),
        unique=True,
    )
    accepted_cgu_signature: Mapped[datetime]
    accepted_cgu_version: Mapped[int]


class UsedQRCode(MappedAsDataclass, Base):
    __tablename__ = "myeclpay_used_qrcode"

    qr_code_id: Mapped[PrimaryKey]
