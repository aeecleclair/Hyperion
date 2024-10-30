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


class QRCodeContent(QRCodeContentBase):
    signature: Base64Bytes


class QRCodeContentData(BaseModel):
    """
    Format of the data stored in the QR code,
    """

    id: UUID
    tot: int
    iat: datetime
    key: UUID
