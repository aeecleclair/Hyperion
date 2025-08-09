from uuid import UUID


class WalletNotFoundOnUpdateError(Exception):
    """
    Exception raised when a wallet is not found during an update operation.
    This should lead to an internal server error response and a rollback of the transaction.
    """

    def __init__(self, wallet_id: UUID):
        super().__init__(f"Wallet {wallet_id} not found when updating")
