from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.myeclpay import models_myeclpay
from app.core.myeclpay.types_myeclpay import (
    TransactionStatus,
    TransactionType,
    WalletType,
)


async def create_wallet(
    wallet_id: UUID,
    wallet_type: WalletType,
    balance: int,
    db: AsyncSession,
) -> None:
    wallet = models_myeclpay.Wallet(
        id=wallet_id,
        type=wallet_type,
        balance=balance,
    )
    db.add(wallet)


async def get_wallet(
    wallet_id: UUID,
    db: AsyncSession,
) -> models_myeclpay.Wallet | None:
    result = await db.execute(
        select(models_myeclpay.Wallet).where(
            models_myeclpay.Wallet.id == wallet_id,
        ),
    )
    return result.scalars().first()


async def get_wallet_device(
    wallet_device_id: UUID,
    db: AsyncSession,
) -> models_myeclpay.WalletDevice | None:
    result = await db.execute(
        select(models_myeclpay.WalletDevice).where(
            models_myeclpay.WalletDevice.id == wallet_device_id,
        ),
    )
    return result.scalars().first()


async def increment_wallet_balance(
    wallet_id: UUID,
    amount: int,
    db: AsyncSession,
) -> None:
    """
    Append `amount` to the wallet balance.
    """
    await db.execute(
        update(models_myeclpay.Wallet)
        .where(models_myeclpay.Wallet.id == wallet_id)
        .values(balance=models_myeclpay.Wallet.balance + amount),
    )


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


async def create_transaction(
    transaction_id: UUID,
    giver_wallet_id: UUID,
    giver_wallet_device_id: UUID,
    receiver_wallet_id: UUID,
    transaction_type: TransactionType,
    seller_user_id: str | None,
    total: int,
    creation: datetime,
    status: TransactionStatus,
    store_note: str | None,
    db: AsyncSession,
) -> None:
    transaction = models_myeclpay.Transaction(
        id=transaction_id,
        giver_wallet_id=giver_wallet_id,
        giver_wallet_device_id=giver_wallet_device_id,
        receiver_wallet_id=receiver_wallet_id,
        transaction_type=transaction_type,
        seller_user_id=seller_user_id,
        total=total,
        creation=creation,
        status=status,
        store_note=store_note,
    )
    db.add(transaction)


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


async def get_seller_by_user_id_and_store_id(
    store_id: UUID,
    user_id: str,
    db: AsyncSession,
) -> models_myeclpay.Seller | None:
    result = await db.execute(
        select(models_myeclpay.Seller).where(
            models_myeclpay.Seller.user_id == user_id,
            models_myeclpay.Seller.store_id == store_id,
        ),
    )
    return result.scalars().first()


async def get_store(
    store_id: UUID,
    db: AsyncSession,
) -> models_myeclpay.Store | None:
    result = await db.execute(
        select(models_myeclpay.Store).where(
            models_myeclpay.Store.id == store_id,
        ),
    )
    return result.scalars().first()


async def create_used_qrcode(
    qr_code_id: UUID,
    db: AsyncSession,
) -> None:
    wallet = models_myeclpay.UsedQRCode(
        qr_code_id=qr_code_id,
    )
    db.add(wallet)


async def get_used_qrcode(
    qr_code_id: UUID,
    db: AsyncSession,
) -> models_myeclpay.UsedQRCode | None:
    result = await db.execute(
        select(models_myeclpay.UsedQRCode).where(
            models_myeclpay.UsedQRCode.qr_code_id == qr_code_id,
        ),
    )
    return result.scalars().first()
