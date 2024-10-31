from datetime import datetime
from uuid import UUID

from pydantic import Base64Bytes, BaseModel

from app.core.myeclpay.types_myeclpay import (
    CGUVersion,
    HistoryType,
    TransactionStatus,
)


class CGUSignature(BaseModel):
    accepted_cgu_version: CGUVersion


class History(BaseModel):
    id: UUID
    type: HistoryType
    other_wallet_name: str
    total: int
    creation: datetime
    status: TransactionStatus


class QRCodeContentBase(BaseModel):
    qr_code_id: UUID
    total: int
    creation: datetime
    walled_device_id: UUID
    # If the QR Code is intended to be scanned for a Store Wallet, or for an other user Wallet
    store: bool


class QRCodeContent(QRCodeContentBase):
    signature: Base64Bytes


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
