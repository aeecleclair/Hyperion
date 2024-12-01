from enum import Enum


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


class HistoryType(str, Enum):
    TRANSFER = "transfer"
    RECEIVED = "received"
    GIVEN = "given"


class TransactionStatus(str, Enum):
    CONFIRMED = "confirmed"
    CANCELED = "canceled"


class RequestStatus(str, Enum):
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    REFUSED = "refused"


class TransferType(str, Enum):
    HELLO_ASSO = "hello_asso"
    CHECK = "check"
    CASH = "cash"
    BANK_TRANSFER = "bank_transfer"
