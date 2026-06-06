from enum import StrEnum

LATEST_TOS = 2
QRCODE_EXPIRATION = 5  # minutes
REQUEST_EXPIRATION = 8  # minutes
RETENTION_DURATION = 10 * 365  # 10 years in days
MYPAYMENT_ROOT = "mypayment"

MYPAYMENT_STRUCTURE_S3_SUBFOLDER = "structures"
MYPAYMENT_STORES_S3_SUBFOLDER = "stores"
MYPAYMENT_USERS_S3_SUBFOLDER = "users"
MYPAYMENT_DEVICES_S3_SUBFOLDER = "devices"
MYPAYMENT_LOGS_S3_SUBFOLDER = "logs"


class WalletType(StrEnum):
    USER = "user"
    STORE = "store"


class WalletDeviceStatus(StrEnum):
    INACTIVE = "inactive"
    ACTIVE = "active"
    REVOKED = "revoked"


class TransactionType(StrEnum):
    # Direct correspond to a QR code payment
    DIRECT = "direct"
    REQUEST = "request"


class HistoryType(StrEnum):
    REFUND = "refund"
    DIRECT_TRANSFER = "direct_transfer"
    REQUEST_TRANSFER = "request_transfer"
    DIRECT_TRANSACTION = "direct_transaction"
    REQUEST_TRANSACTION = "request_transaction"


class HistoryDirection(StrEnum):
    CREDITED = "credited"
    DEBITED = "debited"


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


class TransferOrigin(StrEnum):
    HELLO_ASSO = "hello_asso"


class TransferType(StrEnum):
    # The user transfer money to its own wallet
    DIRECT = "direct"
    # Requests are initiated by the client, who directly transfer the money to the store wallet
    REQUEST = "request"


class ActionType(StrEnum):
    TRANSFER = "transfer"
    REFUND = "refund"
    CANCEL = "cancel"
    TRANSACTION = "transaction"
    WITHDRAWAL = "withdrawal"
    USER_FUSION = "user_fusion"


class RequestType(StrEnum):
    # The user will be redirected to a checkout payment page to complete the transfer
    # The total will be directly credited to the store wallet as a *transfer*
    TRANSFER_REQUEST = "transfer_request"
    # After being accepted by the user, a transaction will be created between the user wallet and the store wallet
    TRANSACTION_REQUEST = "transaction_request"
