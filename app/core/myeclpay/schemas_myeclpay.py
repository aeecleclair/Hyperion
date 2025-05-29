from datetime import datetime
from uuid import UUID

from pydantic import (
    BaseModel,
)

from app.core.memberships import schemas_memberships
from app.core.myeclpay.types_myeclpay import (
    HistoryType,
    TransactionStatus,
    TransactionType,
    TransferType,
    WalletDeviceStatus,
    WalletType,
)
from app.core.users import schemas_users


class StructureBase(BaseModel):
    name: str
    association_membership_id: UUID | None = None
    manager_user_id: str


class Structure(StructureBase):
    id: UUID
    manager_user: schemas_users.CoreUserSimple
    association_membership: schemas_memberships.MembershipSimple | None


class StructureUpdate(BaseModel):
    name: str | None = None
    association_membership_id: UUID | None = None


class StructureTranfert(BaseModel):
    new_manager_user_id: str


class StoreBase(BaseModel):
    name: str


class Store(StoreBase):
    id: UUID
    structure_id: UUID
    wallet_id: UUID
    structure: Structure


class UserStore(Store):
    can_bank: bool
    can_see_history: bool
    can_cancel: bool
    can_manage_sellers: bool


class StoreUpdate(BaseModel):
    name: str | None = None


class SellerCreation(BaseModel):
    user_id: str
    can_bank: bool
    can_see_history: bool
    can_cancel: bool
    can_manage_sellers: bool


class SellerUpdate(BaseModel):
    can_bank: bool | None = None
    can_see_history: bool | None = None
    can_cancel: bool | None = None
    can_manage_sellers: bool | None = None


class Seller(BaseModel):
    user_id: str
    store_id: UUID
    can_bank: bool
    can_see_history: bool
    can_cancel: bool
    can_manage_sellers: bool

    user: schemas_users.CoreUserSimple


class TOSSignature(BaseModel):
    accepted_tos_version: int


class TOSSignatureResponse(BaseModel):
    accepted_tos_version: int
    latest_tos_version: int
    tos_content: str
    max_transaction_total: int
    max_wallet_balance: int


class AdminTransferInfo(BaseModel):
    amount: int
    transfer_type: TransferType
    credited_user_id: str | None = None


class TransferInfo(BaseModel):
    amount: int
    redirect_url: str


class RefundInfo(BaseModel):
    complete_refund: bool
    amount: int | None = None


class HistoryRefund(BaseModel):
    total: int
    creation: datetime


class History(BaseModel):
    id: UUID
    type: HistoryType
    other_wallet_name: str
    total: int
    creation: datetime
    status: TransactionStatus
    refund: HistoryRefund | None = None


class QRCodeContentData(BaseModel):
    """
    Format of the data stored in the QR code.

    This data will be signed using ed25519 and the private key of the WalletDevice that generated the QR Code.

    id: Unique identifier of the QR Code
    tot: Total amount of the transaction, in cents
    iat: Generation datetime of the QR Code
    key: Id of the WalletDevice that generated the QR Code, will be used to verify the signature
    store: If the QR Code is intended to be scanned for a Store Wallet, or for an other user Wallet
    """

    id: UUID
    tot: int
    iat: datetime
    key: UUID
    store: bool


class ScanInfo(QRCodeContentData):
    signature: str
    bypass_membership: bool = False


class Wallet(BaseModel):
    id: UUID
    type: WalletType
    balance: int
    store: Store | None
    user: schemas_users.CoreUser | None


class WalletInfo(BaseModel):
    id: UUID
    type: WalletType
    owner_name: str | None


class WalletDeviceBase(BaseModel):
    name: str


class WalletDevice(WalletDeviceBase):
    id: UUID
    wallet_id: UUID
    creation: datetime
    status: WalletDeviceStatus


class WalletDeviceCreation(WalletDeviceBase):
    ed25519_public_key: bytes


class TransactionBase(BaseModel):
    id: UUID
    debited_wallet_id: UUID
    credited_wallet_id: UUID
    transaction_type: TransactionType

    # User that scanned the qr code
    # Will be None if the transaction is a request
    seller_user_id: str | None

    total: int  # Stored in cents
    creation: datetime
    status: TransactionStatus


class Transaction(TransactionBase):
    refund: "RefundBase | None" = None


class Transfer(BaseModel):
    id: UUID
    type: TransferType
    transfer_identifier: str

    # TODO remove if we only accept hello asso
    approver_user_id: str | None

    wallet_id: UUID
    total: int  # Stored in cents
    creation: datetime
    confirmed: bool


class RefundBase(BaseModel):
    id: UUID
    total: int  # Stored in cents
    creation: datetime
    transaction_id: UUID
    seller_user_id: str | None = None
    credited_wallet_id: UUID
    debited_wallet_id: UUID


class Refund(RefundBase):
    transaction: TransactionBase
    credited_wallet: WalletInfo
    debited_wallet: WalletInfo
