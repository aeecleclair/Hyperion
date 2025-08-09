from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from sqlalchemy import and_, delete, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import noload, selectinload

from app.core.memberships import schemas_memberships
from app.core.mypayment import models_mypayment, schemas_mypayment
from app.core.mypayment.exceptions_mypayment import WalletNotFoundOnUpdateError
from app.core.mypayment.types_mypayment import (
    TransactionStatus,
    WalletDeviceStatus,
    WalletType,
)
from app.core.users import schemas_users


async def create_structure(
    structure: schemas_mypayment.Structure,
    db: AsyncSession,
) -> None:
    db.add(
        models_mypayment.Structure(
            id=structure.id,
            name=structure.name,
            association_membership_id=structure.association_membership_id,
            manager_user_id=structure.manager_user_id,
        ),
    )


async def update_structure(
    structure_id: UUID,
    structure_update: schemas_mypayment.StructureUpdate,
    db: AsyncSession,
) -> None:
    await db.execute(
        update(models_mypayment.Structure)
        .where(models_mypayment.Structure.id == structure_id)
        .values(**structure_update.model_dump(exclude_unset=True)),
    )


async def delete_structure(
    structure_id: UUID,
    db: AsyncSession,
) -> None:
    await db.execute(
        delete(models_mypayment.Structure).where(
            models_mypayment.Structure.id == structure_id,
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
        models_mypayment.StructureManagerTransfert(
            structure_id=structure_id,
            user_id=user_id,
            valid_until=valid_until,
            confirmation_token=confirmation_token,
        ),
    )


async def get_structure_manager_transfer_by_secret(
    confirmation_token: str,
    db: AsyncSession,
) -> models_mypayment.StructureManagerTransfert | None:
    result = await db.execute(
        select(models_mypayment.StructureManagerTransfert).where(
            models_mypayment.StructureManagerTransfert.confirmation_token
            == confirmation_token,
        ),
    )
    return result.scalars().first()


async def delete_structure_manager_transfer_by_structure(
    structure_id: UUID,
    db: AsyncSession,
) -> None:
    await db.execute(
        delete(models_mypayment.StructureManagerTransfert).where(
            models_mypayment.StructureManagerTransfert.structure_id == structure_id,
        ),
    )


async def update_structure_manager(
    structure_id: UUID,
    manager_user_id: str,
    db: AsyncSession,
) -> None:
    await db.execute(
        update(models_mypayment.Structure)
        .where(models_mypayment.Structure.id == structure_id)
        .values(manager_user_id=manager_user_id),
    )


async def get_structures(
    db: AsyncSession,
) -> Sequence[schemas_mypayment.Structure]:
    result = await db.execute(select(models_mypayment.Structure))
    return [
        schemas_mypayment.Structure(
            name=structure.name,
            association_membership_id=structure.association_membership_id,
            association_membership=schemas_memberships.MembershipSimple(
                id=structure.association_membership.id,
                name=structure.association_membership.name,
                manager_group_id=structure.association_membership.manager_group_id,
            )
            if structure.association_membership
            else None,
            manager_user_id=structure.manager_user_id,
            id=structure.id,
            manager_user=schemas_users.CoreUserSimple(
                id=structure.manager_user.id,
                firstname=structure.manager_user.firstname,
                name=structure.manager_user.name,
                nickname=structure.manager_user.nickname,
                account_type=structure.manager_user.account_type,
                school_id=structure.manager_user.school_id,
            ),
        )
        for structure in result.scalars().all()
    ]


async def get_structure_by_id(
    structure_id: UUID,
    db: AsyncSession,
) -> schemas_mypayment.Structure | None:
    structure = (
        (
            await db.execute(
                select(models_mypayment.Structure).where(
                    models_mypayment.Structure.id == structure_id,
                ),
            )
        )
        .scalars()
        .first()
    )
    return (
        schemas_mypayment.Structure(
            name=structure.name,
            association_membership_id=structure.association_membership_id,
            association_membership=schemas_memberships.MembershipSimple(
                id=structure.association_membership.id,
                name=structure.association_membership.name,
                manager_group_id=structure.association_membership.manager_group_id,
            )
            if structure.association_membership
            else None,
            manager_user_id=structure.manager_user_id,
            id=structure.id,
            manager_user=schemas_users.CoreUserSimple(
                id=structure.manager_user.id,
                firstname=structure.manager_user.firstname,
                name=structure.manager_user.name,
                nickname=structure.manager_user.nickname,
                account_type=structure.manager_user.account_type,
                school_id=structure.manager_user.school_id,
            ),
        )
        if structure
        else None
    )


async def create_store(
    store: models_mypayment.Store,
    db: AsyncSession,
) -> None:
    db.add(store)


async def update_store(
    store_id: UUID,
    store_update: schemas_mypayment.StoreUpdate,
    db: AsyncSession,
) -> None:
    await db.execute(
        update(models_mypayment.Store)
        .where(models_mypayment.Store.id == store_id)
        .values(**store_update.model_dump(exclude_none=True)),
    )


async def delete_store(
    store_id: UUID,
    db: AsyncSession,
) -> None:
    await db.execute(
        delete(models_mypayment.Store).where(models_mypayment.Store.id == store_id),
    )


async def get_stores(
    db: AsyncSession,
) -> Sequence[models_mypayment.Store]:
    result = await db.execute(select(models_mypayment.Store))
    return result.scalars().all()


async def get_store_by_name(
    name: str,
    db: AsyncSession,
) -> models_mypayment.Store | None:
    result = await db.execute(
        select(models_mypayment.Store).where(
            models_mypayment.Store.name == name,
        ),
    )
    return result.scalars().first()


async def get_stores_by_structure_id(
    db: AsyncSession,
    structure_id: UUID,
) -> Sequence[models_mypayment.Store]:
    result = await db.execute(
        select(models_mypayment.Store).where(
            models_mypayment.Store.structure_id == structure_id,
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
    db: AsyncSession,
) -> None:
    wallet = models_mypayment.Seller(
        user_id=user_id,
        store_id=store_id,
        can_bank=can_bank,
        can_see_history=can_see_history,
        can_cancel=can_cancel,
        can_manage_sellers=can_manage_sellers,
    )
    db.add(wallet)


async def get_seller(
    user_id: str,
    store_id: UUID,
    db: AsyncSession,
) -> schemas_mypayment.Seller | None:
    result = (
        (
            await db.execute(
                select(models_mypayment.Seller).where(
                    models_mypayment.Seller.user_id == user_id,
                    models_mypayment.Seller.store_id == store_id,
                ),
            )
        )
        .scalars()
        .first()
    )
    return (
        schemas_mypayment.Seller(
            user_id=result.user_id,
            store_id=result.store_id,
            can_bank=result.can_bank,
            can_see_history=result.can_see_history,
            can_cancel=result.can_cancel,
            can_manage_sellers=result.can_manage_sellers,
            user=schemas_users.CoreUserSimple(
                id=result.user.id,
                firstname=result.user.firstname,
                name=result.user.name,
                nickname=result.user.nickname,
                account_type=result.user.account_type,
                school_id=result.user.school_id,
            ),
        )
        if result
        else None
    )


async def get_sellers_by_store_id(
    store_id: UUID,
    db: AsyncSession,
) -> list[schemas_mypayment.Seller]:
    result = await db.execute(
        select(models_mypayment.Seller).where(
            models_mypayment.Seller.store_id == store_id,
        ),
    )
    return [
        schemas_mypayment.Seller(
            user_id=seller.user_id,
            store_id=seller.store_id,
            can_bank=seller.can_bank,
            can_see_history=seller.can_see_history,
            can_cancel=seller.can_cancel,
            can_manage_sellers=seller.can_manage_sellers,
            user=schemas_users.CoreUserSimple(
                id=seller.user.id,
                firstname=seller.user.firstname,
                name=seller.user.name,
                nickname=seller.user.nickname,
                account_type=seller.user.account_type,
                school_id=seller.user.school_id,
            ),
        )
        for seller in result.scalars().all()
    ]


async def get_sellers_by_user_id(
    user_id: str,
    db: AsyncSession,
) -> Sequence[models_mypayment.Seller]:
    result = await db.execute(
        select(models_mypayment.Seller).where(
            models_mypayment.Seller.user_id == user_id,
        ),
    )
    return result.scalars().all()


async def update_seller(
    seller_user_id: str,
    store_id: UUID,
    seller_update: schemas_mypayment.SellerUpdate,
    db: AsyncSession,
) -> None:
    await db.execute(
        update(models_mypayment.Seller)
        .where(
            models_mypayment.Seller.user_id == seller_user_id,
            models_mypayment.Seller.store_id == store_id,
        )
        .values(
            **seller_update.model_dump(exclude_none=True),
        ),
    )


async def delete_seller(
    seller_user_id: str,
    store_id: UUID,
    db: AsyncSession,
) -> None:
    await db.execute(
        delete(models_mypayment.Seller).where(
            models_mypayment.Seller.user_id == seller_user_id,
            models_mypayment.Seller.store_id == store_id,
        ),
    )


async def create_wallet(
    wallet_id: UUID,
    wallet_type: WalletType,
    balance: int,
    db: AsyncSession,
) -> None:
    wallet = models_mypayment.Wallet(
        id=wallet_id,
        type=wallet_type,
        balance=balance,
    )
    db.add(wallet)


async def get_wallets(
    db: AsyncSession,
) -> Sequence[schemas_mypayment.WalletBase]:
    result = await db.execute(select(models_mypayment.Wallet))
    return [
        schemas_mypayment.WalletBase(
            id=wallet.id,
            type=wallet.type,
            balance=wallet.balance,
        )
        for wallet in result.scalars().all()
    ]


async def get_wallet(
    wallet_id: UUID,
    db: AsyncSession,
) -> models_mypayment.Wallet | None:
    # We lock the wallet `for update` to prevent race conditions
    request = (
        select(models_mypayment.Wallet)
        .where(
            models_mypayment.Wallet.id == wallet_id,
        )
        .with_for_update(of=models_mypayment.Wallet)
    )

    result = await db.execute(request)
    return result.scalars().first()


async def get_wallet_device(
    wallet_device_id: UUID,
    db: AsyncSession,
) -> models_mypayment.WalletDevice | None:
    result = await db.execute(
        select(models_mypayment.WalletDevice).where(
            models_mypayment.WalletDevice.id == wallet_device_id,
        ),
    )
    return result.scalars().first()


async def get_wallet_devices_by_wallet_id(
    wallet_id: UUID,
    db: AsyncSession,
) -> Sequence[models_mypayment.WalletDevice]:
    result = await db.execute(
        select(models_mypayment.WalletDevice).where(
            models_mypayment.WalletDevice.wallet_id == wallet_id,
        ),
    )
    return result.scalars().all()


async def get_wallet_device_by_activation_token(
    activation_token: str,
    db: AsyncSession,
) -> models_mypayment.WalletDevice | None:
    result = await db.execute(
        select(models_mypayment.WalletDevice).where(
            models_mypayment.WalletDevice.activation_token == activation_token,
        ),
    )
    return result.scalars().first()


async def create_wallet_device(
    wallet_device: models_mypayment.WalletDevice,
    db: AsyncSession,
) -> None:
    db.add(wallet_device)


async def update_wallet_device_status(
    wallet_device_id: UUID,
    status: WalletDeviceStatus,
    db: AsyncSession,
) -> None:
    await db.execute(
        update(models_mypayment.WalletDevice)
        .where(models_mypayment.WalletDevice.id == wallet_device_id)
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
    # Prevent a race condition by locking the wallet row
    # as we don't want the balance to be modified between the select and the update.
    request = (
        select(models_mypayment.Wallet)
        .where(models_mypayment.Wallet.id == wallet_id)
        .options(
            noload(models_mypayment.Wallet.store),
            noload(models_mypayment.Wallet.user),
        )
        .with_for_update()
    )
    result = await db.execute(request)
    wallet = result.scalars().first()

    if wallet is None:
        raise WalletNotFoundOnUpdateError(wallet_id=wallet_id)
    wallet.balance += amount


async def create_user_payment(
    user_id: str,
    wallet_id: UUID,
    accepted_tos_signature: datetime,
    accepted_tos_version: int,
    db: AsyncSession,
) -> None:
    user_payment = models_mypayment.UserPayment(
        user_id=user_id,
        wallet_id=wallet_id,
        accepted_tos_signature=accepted_tos_signature,
        accepted_tos_version=accepted_tos_version,
    )
    db.add(user_payment)


async def update_user_payment(
    user_id: str,
    accepted_tos_signature: datetime,
    accepted_tos_version: int,
    db: AsyncSession,
) -> None:
    await db.execute(
        update(models_mypayment.UserPayment)
        .where(models_mypayment.UserPayment.user_id == user_id)
        .values(
            accepted_tos_signature=accepted_tos_signature,
            accepted_tos_version=accepted_tos_version,
        ),
    )


async def get_user_payment(
    user_id: str,
    db: AsyncSession,
) -> models_mypayment.UserPayment | None:
    result = await db.execute(
        select(models_mypayment.UserPayment).where(
            models_mypayment.UserPayment.user_id == user_id,
        ),
    )
    return result.scalars().first()


async def create_transaction(
    transaction: schemas_mypayment.TransactionBase,
    debited_wallet_device_id: UUID,
    store_note: str | None,
    db: AsyncSession,
) -> None:
    transaction_db = models_mypayment.Transaction(
        id=transaction.id,
        debited_wallet_id=transaction.debited_wallet_id,
        debited_wallet_device_id=debited_wallet_device_id,
        credited_wallet_id=transaction.credited_wallet_id,
        transaction_type=transaction.transaction_type,
        seller_user_id=transaction.seller_user_id,
        total=transaction.total,
        creation=transaction.creation,
        status=transaction.status,
        store_note=store_note,
        qr_code_id=transaction.qr_code_id,
    )
    db.add(transaction_db)


async def update_transaction_status(
    transaction_id: UUID,
    status: TransactionStatus,
    db: AsyncSession,
) -> None:
    await db.execute(
        update(models_mypayment.Transaction)
        .where(models_mypayment.Transaction.id == transaction_id)
        .values(status=status),
    )


async def get_transaction(
    transaction_id: UUID,
    db: AsyncSession,
) -> schemas_mypayment.Transaction | None:
    # We lock the transaction `for update` to prevent
    # race conditions
    result = (
        (
            await db.execute(
                select(models_mypayment.Transaction)
                .where(
                    models_mypayment.Transaction.id == transaction_id,
                )
                .with_for_update(of=models_mypayment.Transaction),
            )
        )
        .scalars()
        .first()
    )
    return (
        schemas_mypayment.Transaction(
            id=result.id,
            debited_wallet_id=result.debited_wallet_id,
            credited_wallet_id=result.credited_wallet_id,
            transaction_type=result.transaction_type,
            seller_user_id=result.seller_user_id,
            total=result.total,
            creation=result.creation,
            status=result.status,
        )
        if result
        else None
    )


async def get_transactions(
    db: AsyncSession,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    exclude_canceled: bool = False,
) -> Sequence[schemas_mypayment.TransactionBase]:
    result = await db.execute(
        select(models_mypayment.Transaction).where(
            models_mypayment.Transaction.creation >= start_date
            if start_date
            else and_(True),
            models_mypayment.Transaction.creation <= end_date
            if end_date
            else and_(True),
            models_mypayment.Transaction.status != TransactionStatus.CANCELED
            if exclude_canceled
            else and_(True),
        ),
    )
    return [
        schemas_mypayment.TransactionBase(
            id=transaction.id,
            debited_wallet_id=transaction.debited_wallet_id,
            credited_wallet_id=transaction.credited_wallet_id,
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
    start_datetime: datetime | None = None,
    end_datetime: datetime | None = None,
) -> Sequence[models_mypayment.Transaction]:
    result = await db.execute(
        select(models_mypayment.Transaction)
        .where(
            or_(
                models_mypayment.Transaction.debited_wallet_id == wallet_id,
                models_mypayment.Transaction.credited_wallet_id == wallet_id,
            ),
            models_mypayment.Transaction.creation >= start_datetime
            if start_datetime
            else and_(True),
            models_mypayment.Transaction.creation <= end_datetime
            if end_datetime
            else and_(True),
        )
        .options(
            selectinload(models_mypayment.Transaction.debited_wallet),
            selectinload(models_mypayment.Transaction.credited_wallet),
        ),
    )
    return result.scalars().all()


async def get_transfers(
    db: AsyncSession,
    last_checked: datetime | None = None,
) -> Sequence[schemas_mypayment.Transfer]:
    result = await db.execute(
        select(models_mypayment.Transfer).where(
            models_mypayment.Transfer.creation >= last_checked
            if last_checked
            else and_(True),
        ),
    )
    return [
        schemas_mypayment.Transfer(
            id=transfer.id,
            type=transfer.type,
            transfer_identifier=transfer.transfer_identifier,
            approver_user_id=transfer.approver_user_id,
            wallet_id=transfer.wallet_id,
            total=transfer.total,
            creation=transfer.creation,
            confirmed=transfer.confirmed,
        )
        for transfer in result.scalars().all()
    ]


async def create_transfer(
    transfer: schemas_mypayment.Transfer,
    db: AsyncSession,
) -> None:
    transfer_db = models_mypayment.Transfer(
        id=transfer.id,
        type=transfer.type,
        transfer_identifier=transfer.transfer_identifier,
        approver_user_id=transfer.approver_user_id,
        wallet_id=transfer.wallet_id,
        total=transfer.total,
        creation=transfer.creation,
        confirmed=transfer.confirmed,
    )
    db.add(transfer_db)


async def confirm_transfer(
    transfer_id: UUID,
    db: AsyncSession,
) -> None:
    await db.execute(
        update(models_mypayment.Transfer)
        .where(models_mypayment.Transfer.id == transfer_id)
        .values(confirmed=True),
    )


async def get_transfers_by_wallet_id(
    wallet_id: UUID,
    db: AsyncSession,
    start_datetime: datetime | None = None,
    end_datetime: datetime | None = None,
) -> Sequence[models_mypayment.Transfer]:
    result = await db.execute(
        select(models_mypayment.Transfer)
        .where(
            models_mypayment.Transfer.wallet_id == wallet_id,
        )
        .where(
            models_mypayment.Transfer.creation >= start_datetime
            if start_datetime
            else and_(True),
            models_mypayment.Transfer.creation <= end_datetime
            if end_datetime
            else and_(True),
        ),
    )
    return result.scalars().all()


async def get_transfer_by_transfer_identifier(
    db: AsyncSession,
    transfer_identifier: str,
) -> models_mypayment.Transfer | None:
    result = await db.execute(
        select(models_mypayment.Transfer).where(
            models_mypayment.Transfer.transfer_identifier == transfer_identifier,
        ),
    )
    return result.scalars().first()


async def get_refunds(
    db: AsyncSession,
    last_checked: datetime | None = None,
) -> Sequence[schemas_mypayment.RefundBase]:
    result = await db.execute(
        select(models_mypayment.Refund).where(
            models_mypayment.Refund.creation >= last_checked
            if last_checked
            else and_(True),
        ),
    )
    return [
        schemas_mypayment.RefundBase(
            id=refund.id,
            transaction_id=refund.transaction_id,
            credited_wallet_id=refund.credited_wallet_id,
            debited_wallet_id=refund.debited_wallet_id,
            total=refund.total,
            creation=refund.creation,
            seller_user_id=refund.seller_user_id,
        )
        for refund in result.scalars().all()
    ]


async def create_refund(
    refund: schemas_mypayment.RefundBase,
    db: AsyncSession,
) -> None:
    refund_db = models_mypayment.Refund(
        id=refund.id,
        transaction_id=refund.transaction_id,
        credited_wallet_id=refund.credited_wallet_id,
        debited_wallet_id=refund.debited_wallet_id,
        total=refund.total,
        creation=refund.creation,
        seller_user_id=refund.seller_user_id,
    )
    db.add(refund_db)


async def get_refund_by_transaction_id(
    transaction_id: UUID,
    db: AsyncSession,
) -> schemas_mypayment.Refund | None:
    result = (
        (
            await db.execute(
                select(models_mypayment.Refund)
                .where(
                    models_mypayment.Refund.transaction_id == transaction_id,
                )
                .options(
                    selectinload(models_mypayment.Refund.debited_wallet),
                    selectinload(models_mypayment.Refund.credited_wallet),
                ),
            )
        )
        .scalars()
        .first()
    )
    return (
        schemas_mypayment.Refund(
            id=result.id,
            transaction_id=result.transaction_id,
            credited_wallet_id=result.credited_wallet_id,
            debited_wallet_id=result.debited_wallet_id,
            total=result.total,
            creation=result.creation,
            seller_user_id=result.seller_user_id,
            transaction=schemas_mypayment.Transaction(
                id=result.transaction.id,
                debited_wallet_id=result.transaction.debited_wallet_id,
                credited_wallet_id=result.transaction.credited_wallet_id,
                transaction_type=result.transaction.transaction_type,
                seller_user_id=result.transaction.seller_user_id,
                total=result.transaction.total,
                creation=result.transaction.creation,
                status=result.transaction.status,
            ),
            debited_wallet=schemas_mypayment.WalletInfo(
                id=result.debited_wallet.id,
                type=result.debited_wallet.type,
                owner_name=result.debited_wallet.store.name
                if result.debited_wallet.store
                else result.debited_wallet.user.full_name
                if result.debited_wallet.user
                else None,
            ),
            credited_wallet=schemas_mypayment.WalletInfo(
                id=result.credited_wallet.id,
                type=result.credited_wallet.type,
                owner_name=result.credited_wallet.store.name
                if result.credited_wallet.store
                else result.credited_wallet.user.full_name
                if result.credited_wallet.user
                else None,
            ),
        )
        if result
        else None
    )


async def get_refunds_by_wallet_id(
    wallet_id: UUID,
    db: AsyncSession,
    start_datetime: datetime | None = None,
    end_datetime: datetime | None = None,
) -> Sequence[schemas_mypayment.Refund]:
    result = (
        (
            await db.execute(
                select(models_mypayment.Refund).where(
                    or_(
                        models_mypayment.Refund.debited_wallet_id == wallet_id,
                        models_mypayment.Refund.credited_wallet_id == wallet_id,
                    ),
                    models_mypayment.Refund.creation >= start_datetime
                    if start_datetime
                    else and_(True),
                    models_mypayment.Refund.creation <= end_datetime
                    if end_datetime
                    else and_(True),
                ),
            )
        )
        .scalars()
        .all()
    )
    return [
        schemas_mypayment.Refund(
            id=refund.id,
            transaction_id=refund.transaction_id,
            credited_wallet_id=refund.credited_wallet_id,
            debited_wallet_id=refund.debited_wallet_id,
            total=refund.total,
            creation=refund.creation,
            seller_user_id=refund.seller_user_id,
            transaction=schemas_mypayment.Transaction(
                id=refund.transaction.id,
                debited_wallet_id=refund.transaction.debited_wallet_id,
                credited_wallet_id=refund.transaction.credited_wallet_id,
                transaction_type=refund.transaction.transaction_type,
                seller_user_id=refund.transaction.seller_user_id,
                total=refund.transaction.total,
                creation=refund.transaction.creation,
                status=refund.transaction.status,
            ),
            debited_wallet=schemas_mypayment.WalletInfo(
                id=refund.debited_wallet.id,
                type=refund.debited_wallet.type,
                owner_name=refund.debited_wallet.store.name
                if refund.debited_wallet.store
                else refund.debited_wallet.user.full_name
                if refund.debited_wallet.user
                else None,
            ),
            credited_wallet=schemas_mypayment.WalletInfo(
                id=refund.credited_wallet.id,
                type=refund.credited_wallet.type,
                owner_name=refund.credited_wallet.store.name
                if refund.credited_wallet.store
                else refund.credited_wallet.user.full_name
                if refund.credited_wallet.user
                else None,
            ),
        )
        for refund in result
    ]


async def get_store(
    store_id: UUID,
    db: AsyncSession,
) -> models_mypayment.Store | None:
    result = await db.execute(
        select(models_mypayment.Store).where(
            models_mypayment.Store.id == store_id,
        ),
    )
    return result.scalars().first()


async def create_used_qrcode(
    qr_code: schemas_mypayment.ScanInfo,
    db: AsyncSession,
) -> None:
    wallet = models_mypayment.UsedQRCode(
        qr_code_id=qr_code.id,
        qr_code_tot=qr_code.tot,
        qr_code_iat=qr_code.iat,
        qr_code_key=qr_code.key,
        qr_code_store=qr_code.store,
        signature=qr_code.signature,
    )
    db.add(wallet)


async def get_used_qrcode(
    qr_code_id: UUID,
    db: AsyncSession,
) -> models_mypayment.UsedQRCode | None:
    result = await db.execute(
        select(models_mypayment.UsedQRCode).where(
            models_mypayment.UsedQRCode.qr_code_id == qr_code_id,
        ),
    )
    return result.scalars().first()


async def delete_used_qrcode(
    qr_code_id: UUID,
    db: AsyncSession,
) -> None:
    await db.execute(
        delete(models_mypayment.UsedQRCode).where(
            models_mypayment.UsedQRCode.qr_code_id == qr_code_id,
        ),
    )
