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
    INDIRECT = "indirect"
    REQUEST = "request"
    REFUND = "refund"


class HistoryType(str, Enum):
    TRANSFER = "transfer"

    RECEIVED = "received"
    GIVEN = "given"
    INDIRECT_GIVEN = "indirect_given"
    INDIRECT_RECEIVED = "indirect_received"

    REFUND_CREDITED = "refund_credited"
    REFUND_DEBITED = "refund_debited"


class TransactionStatus(str, Enum):
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


class RequestStatus(str, Enum):
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    REFUSED = "refused"


class TransferType(str, Enum):
    HELLO_ASSO = "hello_asso"


class ActionType(str, Enum):
    TRANSFER = "transfer"
    REFUND = "refund"
    CANCEL = "cancel"
    TRANSACTION = "transaction"
    WITHDRAWAL = "withdrawal"


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
            f"User transfer {transfer_id} has already been confirmed",
        )
