import uuid

from pydantic import BaseModel, computed_field


class CheckoutPayment(BaseModel):
    id: uuid.UUID
    paid_amount: int


class Checkout(BaseModel):
    id: uuid.UUID
    payment_url: str


class CheckoutComplete(BaseModel):
    id: uuid.UUID
    module: str

    name: str
    amount: int

    payments: list[CheckoutPayment]

    @computed_field  # type: ignore[misc]
    @property
    def payment_completed(self) -> bool:
        total_paid = sum([payment.paid_amount for payment in self.payments])
        return total_paid == self.amount


class HelloAssoCheckoutMetadata(BaseModel):
    hyperion_checkout_id: str
    secret: str
