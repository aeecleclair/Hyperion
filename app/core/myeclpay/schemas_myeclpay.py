from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.core.myeclpay.types_myeclpay import (
    CGUVersion,
    HistoryType,
    TransactionStatus,
    TransactionType,
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
