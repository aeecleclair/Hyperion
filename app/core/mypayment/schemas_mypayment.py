from datetime import datetime
from uuid import UUID

from pydantic import (
    BaseModel,
    Field,
    model_validator,
)

from app.core.memberships import schemas_memberships
from app.core.mypayment.types_mypayment import (
    HistoryDirection,
    HistoryType,
    RequestStatus,
    TransactionStatus,
    TransactionType,
    TransferOrigin,
    TransferType,
    WalletDeviceStatus,
    WalletType,
)
from app.core.users import schemas_users


class StructureBase(BaseModel):
    short_id: str = Field(
        min_length=3,
        max_length=3,
        description="Short ID of the structure, used for invoices",
    )
    name: str
    association_membership_id: UUID | None = None
    manager_user_id: str
    siege_address_street: str
    siege_address_city: str
    siege_address_zipcode: str
    siege_address_country: str
    siret: str | None = None
    iban: str
    bic: str


class StructureSimple(StructureBase):
    id: UUID
    creation: datetime


class Structure(StructureSimple):
    manager_user: schemas_users.CoreUserSimple
    association_membership: schemas_memberships.MembershipSimple | None
    administrators: list[schemas_users.CoreUserSimple]


class StructureUpdate(BaseModel):
    name: str | None = None
    short_id: str | None = None
    association_membership_id: UUID | None = None
    siret: str | None = None
    siege_address_street: str | None = None
    siege_address_city: str | None = None
    siege_address_zipcode: str | None = None
    siege_address_country: str | None = None
    iban: str | None = None
    bic: str | None = None


class StructureAdministrator(BaseModel):
    user_id: str
    structure_id: UUID


class StructureTranfert(BaseModel):
    new_manager_user_id: str


class StoreBase(BaseModel):
    name: str


class StoreSimple(StoreBase):
    id: UUID
    structure_id: UUID
    wallet_id: UUID
    creation: datetime


class Store(StoreSimple):
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
    can_manage_events: bool = False


class SellerUpdate(BaseModel):
    can_bank: bool | None = None
    can_see_history: bool | None = None
    can_cancel: bool | None = None
    can_manage_sellers: bool | None = None
    can_manage_events: bool | None = None


class Seller(BaseModel):
    user_id: str
    store_id: UUID
    can_bank: bool
    can_see_history: bool
    can_cancel: bool
    can_manage_sellers: bool

    # Event module
    can_manage_events: bool

    user: schemas_users.CoreUserSimple


class TOSSignature(BaseModel):
    accepted_tos_version: int


class TOSSignatureResponse(BaseModel):
    accepted_tos_version: int
    latest_tos_version: int
    tos_content: str
    # TODO: remove this field in the future
    max_transaction_total: int = Field(
        default=0,
        deprecated="The limit is not applied anymore",
    )
    max_wallet_balance: int


class AdminTransferInfo(BaseModel):
    amount: int
    transfer_type: TransferType
    credited_user_id: str | None = None


class TransferInfo(BaseModel):
    amount: int
    redirect_url: str


class StoreTransferInfo(TransferInfo):
    store_id: UUID
    module: str
    object_id: UUID


class RefundInfo(BaseModel):
    complete_refund: bool
    amount: int | None = None


class HistoryRefund(BaseModel):
    total: int
    creation: datetime


class History(BaseModel):
    id: UUID
    type: HistoryType
    direction: HistoryDirection
    other_wallet_name: str
    total: int
    creation: datetime
    status: TransactionStatus
    refund: HistoryRefund | None = None


class WalletBase(BaseModel):
    id: UUID
    type: WalletType
    balance: int


class Wallet(WalletBase):
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

    qr_code_id: UUID | None = None


class Transaction(TransactionBase):
    refund: "RefundBase | None" = None


class TransferCreation(BaseModel):
    id: UUID
    origin: TransferOrigin
    transfer_identifier: str

    # TODO remove if we only accept hello asso
    approver_user_id: str | None

    wallet_id: UUID
    total: int  # Stored in cents
    creation: datetime
    confirmed: bool
    module: str | None
    object_id: UUID | None


class Transfer(TransferCreation):
    type: TransferType


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


class IntegrityCheckHeaders(BaseModel):
    x_data_verifier_token: str


class IntegrityCheckQuery(BaseModel):
    lastChecked: datetime | None = None
    isInitialisation: bool = False


class IntegrityCheckData(BaseModel):
    """Schema for Hyperion data"""

    date: datetime
    wallets: list[WalletBase]
    transactions: list[TransactionBase]
    transfers: list[Transfer]
    refunds: list[RefundBase]


class BankAccountHolderEdit(BaseModel):
    holder_user_id: str


class InvoiceDetailBase(BaseModel):
    invoice_id: UUID
    store_id: UUID
    total: int  # Stored in cents


class InvoiceDetail(InvoiceDetailBase):
    store: StoreSimple


class InvoiceBase(BaseModel):
    id: UUID
    reference: str
    structure_id: UUID
    creation: datetime
    start_date: datetime
    end_date: datetime
    total: int  # Stored in cents
    paid: bool = False
    received: bool = False


class InvoiceInfo(InvoiceBase):
    details: list[InvoiceDetailBase]

    @model_validator(mode="after")
    def validate_sum(self):
        if sum(detail.total for detail in self.details) != self.total:
            raise ValueError
        return self


class Invoice(InvoiceBase):
    structure: Structure
    details: list[InvoiceDetail]

    @model_validator(mode="after")
    def validate_details(self):
        if sum(detail.total for detail in self.details) != self.total:
            raise ValueError
        return self


class Withdrawal(BaseModel):
    id: UUID
    wallet_id: UUID
    total: int  # Stored in cents
    creation: datetime


class Request(BaseModel):
    id: UUID
    wallet_id: UUID
    creation: datetime
    expiration_date: datetime
    total: int  # Stored in cents
    store_id: UUID
    name: str
    store_note: str | None = None
    module: str  # module root, will be used to call the payment callback with the provided object_id
    object_id: UUID
    status: RequestStatus
    transaction_id: UUID | None = None


class RequestEdit(BaseModel):
    name: str | None = None
    store_note: str | None = None
    status: RequestStatus | None = None
    transaction_id: UUID | None = None


class RequestInfo(BaseModel):
    store_id: UUID
    total: int
    request_name: str
    store_note: str | None
    module: str
    # Id of the object from the module, this id will be passed to the module in the transaction callback
    object_id: UUID


class PaymentInfo(RequestInfo):
    redirect_url: str


class SecuredContentData(BaseModel):
    """
    Format of the data stored in the payment order.

    This data will be signed using ed25519 and the private key of the WalletDevice that generated the payment order

    id: Unique identifier of the payment
    tot: Total amount of the transaction, in cents
    iat: Generation datetime of the payment order
    key: Id of the WalletDevice that generated the payment order, will be used to get the public key to verify the signature
    store: If the payment is intended to be banked by a store or by an other user
    """

    id: UUID
    tot: int
    iat: datetime
    key: UUID
    store: bool


class SignedContent(SecuredContentData):
    signature: str


class ScanInfo(SignedContent):
    bypass_membership: bool = False


class PaymentRequestInfo(BaseModel):
    end_date: datetime
    checkout_url: str | None = None
