from enum import Enum
from uuid import UUID


class WalletType(str, Enum):
    USER = "user"
    STORE = "store"


class WalletDeviceStatus(str, Enum):
    INACTIVE = "inactive"
    ACTIVE = "active"
    REVOKED = "revoked"


class TransactionType(str, Enum):
    DIRECT = "direct"
    REQUEST = "request"
    REFUND = "refund"


class HistoryType(str, Enum):
    TRANSFER = "transfer"
    RECEIVED = "received"
    GIVEN = "given"


class TransactionStatus(str, Enum):
    CONFIRMED = "confirmed"
    CANCELED = "canceled"
    REFUNDED = "refunded"


class RequestStatus(str, Enum):
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    REFUSED = "refused"


class TransferType(str, Enum):
    HELLO_ASSO = "hello_asso"
    CHECK = "check"
    CASH = "cash"
    BANK_TRANSFER = "bank_transfer"


class UnexpectedError(Exception):
    pass


class TransferNotFoundByCallbackError(Exception):
    def __init__(self, checkout_id: UUID):
        super().__init__(f"User transfer {checkout_id} not found.")


class TransferTotalDontMatchInCallbackError(Exception):
    def __init__(self, transfer_id: UUID):
        super().__init__(
            f"User transfer {transfer_id} amount does not match the paid amount",
        )


class TransferAlreadyConfirmedInCallbackError(Exception):
    def __init__(self, transfer_id: UUID):
        super().__init__(
            f"User transfer {transfer_id} amount does not match the paid amount",
        )
