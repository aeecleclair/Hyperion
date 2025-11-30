import uuid

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.types.sqlalchemy import Base, PrimaryKey


class CheckoutPayment(Base):
    __tablename__ = "checkout_checkout_payment"

    id: Mapped[PrimaryKey]
    checkout_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("checkout_checkout.id"))

    paid_amount: Mapped[int]
    hello_asso_payment_id: Mapped[int] = mapped_column(index=True, unique=True)


class Checkout(Base):
    """
    The checkout table store data about HelloAsso checkouts.
    """

    __tablename__ = "checkout_checkout"

    id: Mapped[PrimaryKey]
    # Module should match the module root for the payment callback to be called
    module: Mapped[str]

    name: Mapped[str]
    amount: Mapped[int]

    hello_asso_checkout_id: Mapped[int]

    # A secret defined by Hyperion and included in the checkout metadata dict
    # to ensure the webhook call was made by HelloAsso
    secret: Mapped[str]

    payments: Mapped[list[CheckoutPayment]] = relationship(default_factory=list)
