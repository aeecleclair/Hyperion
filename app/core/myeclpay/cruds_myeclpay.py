from datetime import datetime
from typing import Sequence
from uuid import UUID

from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.myeclpay import models_myeclpay
from app.core.myeclpay.types_myeclpay import WalletType


async def create_wallet(
    wallet_id: UUID,
    type: WalletType,
    balance: int,
    db: AsyncSession,
) -> None:
    wallet = models_myeclpay.Wallet(
        id=wallet_id,
        type=type,
        balance=balance,
    )
    db.add(wallet)


async def create_user_payment(
    user_id: str,
    wallet_id: UUID,
    accepted_cgu_signature: datetime,
    accepted_cgu_version: int,
    db: AsyncSession,
) -> None:
    user_payment = models_myeclpay.UserPayment(
        user_id=user_id,
        wallet_id=wallet_id,
        accepted_cgu_signature=accepted_cgu_signature,
        accepted_cgu_version=accepted_cgu_version,
    )
    db.add(user_payment)


async def update_user_payment(
    user_id: str,
    accepted_cgu_signature: datetime,
    accepted_cgu_version: int,
    db: AsyncSession,
) -> None:
    await db.execute(
        update(models_myeclpay.UserPayment)
        .where(models_myeclpay.UserPayment.user_id == user_id)
        .values(
            accepted_cgu_signature=accepted_cgu_signature,
            accepted_cgu_version=accepted_cgu_version,
        ),
    )


async def get_user_payment(
    user_id: str,
    db: AsyncSession,
) -> models_myeclpay.UserPayment | None:
    result = await db.execute(
        select(models_myeclpay.UserPayment).where(
            models_myeclpay.UserPayment.user_id == user_id,
        ),
    )
    return result.scalars().first()


async def get_transactions_by_wallet_id(
    wallet_id: UUID,
    db: AsyncSession,
) -> Sequence[models_myeclpay.Transaction]:
    result = await db.execute(
        select(models_myeclpay.Transaction)
        .where(
            or_(
                models_myeclpay.Transaction.giver_wallet_id == wallet_id,
                models_myeclpay.Transaction.receiver_wallet_id == wallet_id,
            ),
        )
        .options(
            selectinload(models_myeclpay.Transaction.giver_wallet),
            selectinload(models_myeclpay.Transaction.receiver_wallet),
        ),
    )
    return result.scalars().all()


async def get_transfers_by_wallet_id(
    wallet_id: UUID,
    db: AsyncSession,
) -> Sequence[models_myeclpay.Transfer]:
    result = await db.execute(
        select(models_myeclpay.Transfer).where(
            models_myeclpay.Transfer.wallet_id == wallet_id,
        ),
    )
    return result.scalars().all()
