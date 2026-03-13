from enum import StrEnum


class WalletType(StrEnum):
    USER = "user"
    STORE = "store"


class WalletDeviceStatus(StrEnum):
    INACTIVE = "inactive"
    ACTIVE = "active"
    REVOKED = "revoked"


class TransactionType(StrEnum):
    DIRECT = "direct"
    REQUEST = "request"
    REFUND = "refund"


class HistoryType(StrEnum):
    TRANSFER = "transfer"
    RECEIVED = "received"
    GIVEN = "given"
    REFUND_CREDITED = "refund_credited"
    REFUND_DEBITED = "refund_debited"


class TransactionStatus(StrEnum):
    """
    CONFIRMED: The transaction has been confirmed and is complete.
    CANCELED: The transaction has been canceled. It is used for transfer requests, for which the user has 15 minutes to complete the HelloAsso checkout
    REFUNDED: The transaction between to wallets has been partially or totally refunded.
    PENDING: The transaction is pending and has not yet been completed. It is used for transfer requests, for which the user has 15 minutes to complete the HelloAsso checkout
    """

    CONFIRMED = "confirmed"
    CANCELED = "canceled"
    REFUNDED = "refunded"
    PENDING = "pending"


class RequestStatus(StrEnum):
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    REFUSED = "refused"
    EXPIRED = "expired"


class TransferType(StrEnum):
    HELLO_ASSO = "hello_asso"


class ActionType(StrEnum):
    TRANSFER = "transfer"
    REFUND = "refund"
    CANCEL = "cancel"
    TRANSACTION = "transaction"
    WITHDRAWAL = "withdrawal"
