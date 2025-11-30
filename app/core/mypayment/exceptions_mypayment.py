from uuid import UUID


class WalletNotFoundOnUpdateError(Exception):
    """
    Exception raised when a wallet is not found during an update operation.
    This should lead to an internal server error response and a rollback of the transaction.
    """

    def __init__(self, wallet_id: UUID):
        super().__init__(f"Wallet {wallet_id} not found when updating")


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
