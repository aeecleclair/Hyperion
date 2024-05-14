from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.types.sqlalchemy import Base, PrimaryKey


class CheckoutPayment(Base):
    __tablename__ = "payment_checkout_payment"

    id: Mapped[PrimaryKey]

    paid_amount: Mapped[int]
    hello_asso_payment_id: Mapped[str] = mapped_column(index=True, unique=True)


class Checkout(Base):
    """
    The checkout table store data about HelloAsso checkouts.
    """

    __tablename__ = "payment_checkout"

    id: Mapped[PrimaryKey]
    module: Mapped[str]

    name: Mapped[str]
    amount: Mapped[int]

    hello_asso_checkout_id: Mapped[str]
    hello_asso_order_id: Mapped[str | None]

    payments: Mapped[list[CheckoutPayment]] = relationship()
