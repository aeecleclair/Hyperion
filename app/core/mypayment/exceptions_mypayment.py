from uuid import UUID

from app.core.checkout.types_checkout import HelloAssoConfigName
from app.core.mypayment.types_mypayment import RequestType, WalletType


class WalletNotFoundOnUpdateError(Exception):
    """
    Exception raised when a wallet is not found during an update operation.
    This should lead to an internal server error response and a rollback of the transaction.
    """

    def __init__(self, wallet_id: UUID):
        super().__init__(f"Wallet {wallet_id} not found when updating")


class LinkedWalletNotFoundError(Exception):
    """
    Exception raised when a wallet linked to a transaction is not found.
    This should lead to an internal server error response and a rollback of the transaction.
    """

    def __init__(self, wallet_id: UUID):
        super().__init__(f"Linked wallet {wallet_id} not found for transaction")


class InvalidWalletTypeError(Exception):
    """
    Exception raised when a wallet has an invalid type for the operation being performed.
    This should lead to an internal server error response and a rollback of the transaction.
    """

    def __init__(self, wallet_id: UUID, expected_type: WalletType):
        super().__init__(
            f"Wallet {wallet_id} has an invalid type. Expected type: {expected_type.name}",
        )


class InvoiceNotFoundAfterCreationError(Exception):
    """
    Exception raised when an invoice is not found after its creation.
    This should lead to an internal server error response and a rollback of the transaction.
    """

    def __init__(self, invoice_id: UUID):
        super().__init__(f"Invoice {invoice_id} not found after creation")


class ReferencedStructureNotFoundError(Exception):
    """
    Exception raised when a referenced structure is not found.
    This should lead to an internal server error response and a rollback of the transaction.
    """

    def __init__(self, structure_id: UUID):
        super().__init__(f"Referenced structure {structure_id} not found")


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


class PaymentUserNotFoundError(Exception):
    def __init__(self, user_id: str):
        super().__init__(
            f"User {user_id} does not have a payment account",
        )


class InvalidRequestTypeError(Exception):
    def __init__(self, request_type: RequestType):
        super().__init__(
            f"Request type {request_type.name} is not supported",
        )


class InvalidCheckoutToolError(Exception):
    def __init__(self, name: HelloAssoConfigName):
        super().__init__(
            f"Checkout tool {name.name} is not supported",
        )


class UnlinkedValidatedRequestError(Exception):
    def __init__(self, request_id: UUID):
        super().__init__(
            f"Request {request_id} has been validated but is not linked to any transfer or transaction",
        )


class PaiementObjectNotFoundError(Exception):
    def __init__(self, object_id: UUID):
        super().__init__(
            f"Payment object with id {object_id} not found",
        )


class InvalidRefundOnTransferError(Exception):
    def __init__(self, transfer_id: UUID):
        super().__init__(
            f"Transfer {transfer_id} cannot be refunded as it does not have an approver_user_id",
        )
