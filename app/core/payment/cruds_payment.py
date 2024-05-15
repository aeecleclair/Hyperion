import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.payment import models_payment


async def create_checkout(
    db: AsyncSession,
    checkout: models_payment.Checkout,
) -> models_payment.Checkout:
    db.add(checkout)
    try:
        await db.commit()
        return checkout
    except IntegrityError as error:
        await db.rollback()
        raise ValueError(error)


async def get_checkout_by_id(
    checkout_id: uuid.UUID,
    db: AsyncSession,
) -> models_payment.Checkout | None:
    result = await db.execute(
        select(models_payment.Checkout).where(
            models_payment.Checkout.id == checkout_id,
        ),
    )
    return result.scalars().first()


async def create_checkout_payment(
    db: AsyncSession,
    checkout_payment: models_payment.CheckoutPayment,
) -> models_payment.CheckoutPayment:
    db.add(checkout_payment)
    try:
        await db.commit()
        return checkout_payment
    except IntegrityError as error:
        await db.rollback()
        raise ValueError(error)


async def get_checkout_payment_by_hello_asso_payment_id(
    hello_asso_payment_id: str,
    db: AsyncSession,
) -> models_payment.CheckoutPayment | None:
    result = await db.execute(
        select(models_payment.CheckoutPayment).where(
            models_payment.CheckoutPayment.hello_asso_payment_id
            == hello_asso_payment_id,
        ),
    )
    return result.scalars().first()
