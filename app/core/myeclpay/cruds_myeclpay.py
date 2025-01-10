from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.myeclpay import models_myeclpay, schemas_myeclpay
from app.core.myeclpay.types_myeclpay import (
    TransactionStatus,
    TransactionType,
    WalletDeviceStatus,
    WalletType,
)


async def create_structure(
    structure: schemas_myeclpay.Structure,
    db: AsyncSession,
) -> None:
    db.add(
        models_myeclpay.Structure(
            id=structure.id,
            name=structure.name,
            membership=structure.membership,
            manager_user_id=structure.manager_user_id,
        ),
    )


async def update_structure(
    structure_id: UUID,
    structure_update: schemas_myeclpay.StructureUpdate,
    db: AsyncSession,
) -> None:
    await db.execute(
        update(models_myeclpay.Structure)
        .where(models_myeclpay.Structure.id == structure_id)
        .values(**structure_update.model_dump(exclude_none=True)),
    )


async def delete_structure(
    structure_id: UUID,
    db: AsyncSession,
) -> None:
    await db.execute(
        delete(models_myeclpay.Structure).where(
            models_myeclpay.Structure.id == structure_id,
        ),
    )


async def init_structure_manager_transfer(
    structure_id: UUID,
    user_id: str,
    valid_until: datetime,
    confirmation_token: str,
    db: AsyncSession,
) -> None:
    db.add(
        models_myeclpay.StructureManagerTransfert(
            structure_id=structure_id,
            user_id=user_id,
            valid_until=valid_until,
            confirmation_token=confirmation_token,
        ),
    )
    await db.commit()


async def get_structure_manager_transfer_by_secret(
    confirmation_token: str,
    db: AsyncSession,
) -> models_myeclpay.StructureManagerTransfert | None:
    result = await db.execute(
        select(models_myeclpay.StructureManagerTransfert).where(
            models_myeclpay.StructureManagerTransfert.confirmation_token
            == confirmation_token,
        ),
    )
    return result.scalars().first()


async def delete_structure_manager_transfer_by_structure(
    structure_id: UUID,
    db: AsyncSession,
) -> None:
    await db.execute(
        delete(models_myeclpay.StructureManagerTransfert).where(
            models_myeclpay.StructureManagerTransfert.structure_id == structure_id,
        ),
    )


async def update_structure_manager(
    structure_id: UUID,
    manager_user_id: str,
    db: AsyncSession,
) -> None:
    await db.execute(
        update(models_myeclpay.Structure)
        .where(models_myeclpay.Structure.id == structure_id)
        .values(manager_user_id=manager_user_id),
    )


async def get_structures(
    db: AsyncSession,
) -> Sequence[schemas_myeclpay.Structure]:
    result = await db.execute(select(models_myeclpay.Structure))
    return [
        schemas_myeclpay.Structure(
            name=structure.name,
            membership=structure.membership,
            manager_user_id=structure.manager_user_id,
            id=structure.id,
        )
        for structure in result.scalars().all()
    ]


async def get_structure_by_id(
    structure_id: UUID,
    db: AsyncSession,
) -> schemas_myeclpay.Structure | None:
    structure = (
        (
            await db.execute(
                select(models_myeclpay.Structure).where(
                    models_myeclpay.Structure.id == structure_id,
                ),
            )
        )
        .scalars()
        .first()
    )
    return (
        schemas_myeclpay.Structure(
            name=structure.name,
            membership=structure.membership,
            manager_user_id=structure.manager_user_id,
            id=structure.id,
        )
        if structure
        else None
    )


async def create_store(
    store: models_myeclpay.Store,
    db: AsyncSession,
) -> None:
    db.add(store)


async def update_store(
    store_id: UUID,
    store_update: schemas_myeclpay.StoreUpdate,
    db: AsyncSession,
) -> None:
    await db.execute(
        update(models_myeclpay.Store)
        .where(models_myeclpay.Store.id == store_id)
        .values(**store_update.model_dump(exclude_none=True)),
    )
    await db.commit()


async def get_stores(
    db: AsyncSession,
) -> Sequence[models_myeclpay.Store]:
    result = await db.execute(select(models_myeclpay.Store))
    return result.scalars().all()


async def get_stores_by_structure_id(
    db: AsyncSession,
    structure_id: UUID,
) -> Sequence[models_myeclpay.Store]:
    result = await db.execute(
        select(models_myeclpay.Store).where(
            models_myeclpay.Store.structure_id == structure_id,
        ),
    )
    return result.scalars().all()


async def create_seller(
    user_id: str,
    store_id: UUID,
    can_bank: bool,
    can_see_history: bool,
    can_cancel: bool,
    can_manage_sellers: bool,
    store_admin: bool,
    db: AsyncSession,
) -> None:
    wallet = models_myeclpay.Seller(
        user_id=user_id,
        store_id=store_id,
        can_bank=can_bank,
        can_see_history=can_see_history,
        can_cancel=can_cancel,
        can_manage_sellers=can_manage_sellers,
        store_admin=store_admin,
    )
    db.add(wallet)


async def get_admin_sellers(
    store_id: UUID,
    db: AsyncSession,
) -> Sequence[models_myeclpay.Seller]:
    result = await db.execute(
        select(models_myeclpay.Seller)
        .where(
            models_myeclpay.Seller.store_id == store_id,
            models_myeclpay.Seller.store_admin.is_(True),
        )
        .options(selectinload(models_myeclpay.Seller.user)),
    )
    return result.scalars().all()


async def get_seller(
    seller_user_id: str,
    store_id: UUID,
    db: AsyncSession,
) -> models_myeclpay.Seller | None:
    result = await db.execute(
        select(models_myeclpay.Seller).where(
            models_myeclpay.Seller.user_id == seller_user_id,
            models_myeclpay.Seller.store_id == store_id,
        ),
    )
    return result.scalars().first()


async def update_seller(
    seller_user_id: str,
    store_id: UUID,
    can_bank: bool,
    can_see_history: bool,
    can_cancel: bool,
    can_manage_sellers: bool,
    store_admin: bool,
    db: AsyncSession,
) -> None:
    await db.execute(
        update(models_myeclpay.Seller)
        .where(
            models_myeclpay.Seller.user_id == seller_user_id,
            models_myeclpay.Seller.store_id == store_id,
        )
        .values(
            can_bank=can_bank,
            can_see_history=can_see_history,
            can_cancel=can_cancel,
            can_manage_sellers=can_manage_sellers,
            store_admin=store_admin,
        ),
    )


async def delete_seller(
    seller_user_id: str,
    store_id: UUID,
    db: AsyncSession,
) -> None:
    await db.execute(
        delete(models_myeclpay.Seller).where(
            models_myeclpay.Seller.user_id == seller_user_id,
            models_myeclpay.Seller.store_id == store_id,
        ),
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


async def get_wallets(
    db: AsyncSession,
) -> Sequence[schemas_myeclpay.Wallet]:
    result = await db.execute(select(models_myeclpay.Wallet))
    return [
        schemas_myeclpay.Wallet(
            id=wallet.id,
            type=wallet.type,
            balance=wallet.balance,
            store=wallet.store,
            user=wallet.user,
        )
        for wallet in result.scalars().all()
    ]


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


async def get_wallet_devices_by_wallet_id(
    wallet_id: UUID,
    db: AsyncSession,
) -> Sequence[models_myeclpay.WalletDevice]:
    result = await db.execute(
        select(models_myeclpay.WalletDevice).where(
            models_myeclpay.WalletDevice.wallet_id == wallet_id,
        ),
    )
    return result.scalars().all()


async def get_wallet_device_by_activation_token(
    activation_token: str,
    db: AsyncSession,
) -> models_myeclpay.WalletDevice | None:
    result = await db.execute(
        select(models_myeclpay.WalletDevice).where(
            models_myeclpay.WalletDevice.activation_token == activation_token,
        ),
    )
    return result.scalars().first()


async def create_wallet_device(
    wallet_device: models_myeclpay.WalletDevice,
    db: AsyncSession,
) -> None:
    db.add(wallet_device)


async def update_wallet_device_status(
    wallet_device_id: UUID,
    status: WalletDeviceStatus,
    db: AsyncSession,
) -> None:
    await db.execute(
        update(models_myeclpay.WalletDevice)
        .where(models_myeclpay.WalletDevice.id == wallet_device_id)
        .values(status=status),
    )


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


async def get_transactions(
    db: AsyncSession,
) -> Sequence[schemas_myeclpay.Transaction]:
    result = await db.execute(select(models_myeclpay.Transaction))
    return [
        schemas_myeclpay.Transaction(
            id=transaction.id,
            giver_wallet_id=transaction.giver_wallet_id,
            receiver_wallet_id=transaction.receiver_wallet_id,
            transaction_type=transaction.transaction_type,
            seller_user_id=transaction.seller_user_id,
            total=transaction.total,
            creation=transaction.creation,
            status=transaction.status,
        )
        for transaction in result.scalars().all()
    ]


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


async def get_transfers(
    db: AsyncSession,
) -> Sequence[schemas_myeclpay.Transfer]:
    result = await db.execute(select(models_myeclpay.Transfer))
    return [
        schemas_myeclpay.Transfer(
            id=transfer.id,
            type=transfer.type,
            transfer_identifier=transfer.transfer_identifier,
            approver_user_id=transfer.approver_user_id,
            wallet_id=transfer.wallet_id,
            total=transfer.total,
            creation=transfer.creation,
        )
        for transfer in result.scalars().all()
    ]


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


async def get_all_user_sellers(
    user_id: str,
    db: AsyncSession,
) -> Sequence[models_myeclpay.Seller]:
    result = await db.execute(
        select(models_myeclpay.Seller).where(
            models_myeclpay.Seller.user_id == user_id,
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
