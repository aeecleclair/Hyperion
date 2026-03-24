import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.checkout import models_checkout, schemas_checkout


async def create_checkout(
    db: AsyncSession,
    checkout: models_checkout.Checkout,
) -> models_checkout.Checkout:
    db.add(checkout)

    return checkout


async def get_checkouts(
    module: str,
    db: AsyncSession,
    last_checked: datetime | None = None,
) -> list[schemas_checkout.CheckoutComplete]:
    result = await db.execute(
        select(models_checkout.Checkout)
        .options(selectinload(models_checkout.Checkout.payments))
        .where(
            models_checkout.Checkout.module == module,
        ),
    )
    return [
        schemas_checkout.CheckoutComplete(
            id=checkout.id,
            module=checkout.module,
            name=checkout.name,
            amount=checkout.amount,
            payments=[
                schemas_checkout.CheckoutPayment(
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
) -> models_checkout.Checkout | None:
    result = await db.execute(
        select(models_checkout.Checkout)
        .where(
            models_checkout.Checkout.id == checkout_id,
        )
        .options(selectinload(models_checkout.Checkout.payments)),
    )
    return result.scalars().first()


async def get_checkout_by_hello_asso_checkout_id(
    hello_asso_checkout_id: int,
    db: AsyncSession,
) -> models_checkout.Checkout | None:
    result = await db.execute(
        select(models_checkout.Checkout).where(
            models_checkout.Checkout.hello_asso_checkout_id == hello_asso_checkout_id,
        ),
    )
    return result.scalars().first()


async def create_checkout_payment(
    db: AsyncSession,
    checkout_payment: models_checkout.CheckoutPayment,
) -> models_checkout.CheckoutPayment:
    db.add(checkout_payment)
    await db.flush()
    return checkout_payment


async def get_checkout_payment_by_hello_asso_payment_id(
    hello_asso_payment_id: int,
    db: AsyncSession,
) -> models_checkout.CheckoutPayment | None:
    result = await db.execute(
        select(models_checkout.CheckoutPayment).where(
            models_checkout.CheckoutPayment.hello_asso_payment_id
            == hello_asso_payment_id,
        ),
    )
    return result.scalars().first()
