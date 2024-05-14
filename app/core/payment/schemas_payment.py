import uuid

from pydantic import BaseModel, computed_field


class CheckoutPayment(BaseModel):
    id: uuid
    paid_amount: int


class Checkout(BaseModel):
    id: uuid
    payment_url: str


class CheckoutComplete(BaseModel):
    id: uuid
    module: str

    name: str
    amount: int

    payments: list[CheckoutPayment]

    @computed_field
    @property
    def payment_completed(self) -> bool:
        total_paid = sum([payment.amount for payment in self.payments])
        return total_paid == self.amount
