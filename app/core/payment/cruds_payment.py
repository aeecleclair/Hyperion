import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.payment import models_payment, schemas_payment


async def create_checkout(
    db: AsyncSession,
    checkout: models_payment.Checkout,
) -> models_payment.Checkout:
    db.add(checkout)

    return checkout


async def get_checkouts(
    module: str,
    db: AsyncSession,
    last_checked: datetime | None = None,
) -> list[schemas_payment.CheckoutComplete]:
    result = await db.execute(
        select(models_payment.Checkout)
        .options(selectinload(models_payment.Checkout.payments))
        .where(
            models_payment.Checkout.module == module,
        ),
    )
    return [
        schemas_payment.CheckoutComplete(
            id=checkout.id,
            module=checkout.module,
            name=checkout.name,
            amount=checkout.amount,
            payments=[
                schemas_payment.CheckoutPayment(
                    id=payment.id,
                    checkout_id=payment.checkout_id,
                    paid_amount=payment.paid_amount,
                )
                for payment in checkout.payments
            ],
        )
        for checkout in result.scalars().all()
    ]


async def get_checkout_by_id(
    checkout_id: uuid.UUID,
    db: AsyncSession,
) -> models_payment.Checkout | None:
    result = await db.execute(
        select(models_payment.Checkout)
        .where(
            models_payment.Checkout.id == checkout_id,
        )
        .options(selectinload(models_payment.Checkout.payments)),
    )
    return result.scalars().first()


async def get_checkout_by_hello_asso_checkout_id(
    hello_asso_checkout_id: int,
    db: AsyncSession,
) -> models_payment.Checkout | None:
    result = await db.execute(
        select(models_payment.Checkout).where(
            models_payment.Checkout.hello_asso_checkout_id == hello_asso_checkout_id,
        ),
    )
    return result.scalars().first()


async def create_checkout_payment(
    db: AsyncSession,
    checkout_payment: models_payment.CheckoutPayment,
) -> models_payment.CheckoutPayment:
    db.add(checkout_payment)
    await db.flush()
    return checkout_payment


async def get_checkout_payment_by_hello_asso_payment_id(
    hello_asso_payment_id: int,
    db: AsyncSession,
) -> models_payment.CheckoutPayment | None:
    result = await db.execute(
        select(models_payment.CheckoutPayment).where(
            models_payment.CheckoutPayment.hello_asso_payment_id
            == hello_asso_payment_id,
        ),
    )
    return result.scalars().first()
