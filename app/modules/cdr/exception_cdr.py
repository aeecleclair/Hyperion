from uuid import UUID


class PurchaseUserNotFoundError(Exception):
    """Raised when a user is not found for a purchase."""

    def __init__(self, user_id: str):
        self.user_id = user_id
        super().__init__(f"User with ID {user_id} not found for the purchase.")


class ProductAssociationMembershipNotFoundError(Exception):
    """Raised when a product is not found for an association membership."""

    def __init__(self, product_id: UUID):
        self.product_id = product_id
        super().__init__(
            f"Product with ID {product_id} not found for the association membership.",
        )
