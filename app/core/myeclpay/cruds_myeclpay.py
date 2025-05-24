from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.memberships import schemas_memberships
from app.core.myeclpay import models_myeclpay, schemas_myeclpay
from app.core.myeclpay.types_myeclpay import (
    TransactionStatus,
    WalletDeviceStatus,
    WalletType,
)
from app.core.users import schemas_users


async def create_structure(
    structure: schemas_myeclpay.Structure,
    db: AsyncSession,
) -> None:
    db.add(
        models_myeclpay.Structure(
            id=structure.id,
            name=structure.name,
            association_membership_id=structure.association_membership_id,
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
        .values(**structure_update.model_dump(exclude_unset=True)),
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


async def delete_store(
    store_id: UUID,
    db: AsyncSession,
) -> None:
    await db.execute(
        delete(models_myeclpay.Store).where(models_myeclpay.Store.id == store_id),
    )


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
    db: AsyncSession,
) -> None:
    wallet = models_myeclpay.Seller(
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
) -> schemas_myeclpay.Seller | None:
    result = (
        (
            await db.execute(
                select(models_myeclpay.Seller).where(
                    models_myeclpay.Seller.user_id == user_id,
                    models_myeclpay.Seller.store_id == store_id,
                ),
            )
        )
        .scalars()
        .first()
    )
    return (
        schemas_myeclpay.Seller(
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
) -> list[schemas_myeclpay.Seller]:
    result = await db.execute(
        select(models_myeclpay.Seller).where(
            models_myeclpay.Seller.store_id == store_id,
        ),
    )
    return [
        schemas_myeclpay.Seller(
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
) -> Sequence[models_myeclpay.Seller]:
    result = await db.execute(
        select(models_myeclpay.Seller).where(
            models_myeclpay.Seller.user_id == user_id,
        ),
    )
    return result.scalars().all()


async def update_seller(
    seller_user_id: str,
    store_id: UUID,
    seller_update: schemas_myeclpay.SellerUpdate,
    db: AsyncSession,
) -> None:
    await db.execute(
        update(models_myeclpay.Seller)
        .where(
            models_myeclpay.Seller.user_id == seller_user_id,
            models_myeclpay.Seller.store_id == store_id,
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
            store=schemas_myeclpay.Store(
                id=wallet.store.id,
                name=wallet.store.name,
                structure_id=wallet.store.structure_id,
                structure=schemas_myeclpay.Structure(
                    id=wallet.store.structure.id,
                    name=wallet.store.structure.name,
                    association_membership_id=wallet.store.structure.association_membership_id,
                    association_membership=schemas_memberships.MembershipSimple(
                        id=wallet.store.structure.association_membership.id,
                        name=wallet.store.structure.association_membership.name,
                        manager_group_id=wallet.store.structure.association_membership.manager_group_id,
                    )
                    if wallet.store.structure.association_membership
                    else None,
                    manager_user_id=wallet.store.structure.manager_user_id,
                    manager_user=schemas_users.CoreUserSimple(
                        id=wallet.store.structure.manager_user.id,
                        firstname=wallet.store.structure.manager_user.firstname,
                        name=wallet.store.structure.manager_user.name,
                        nickname=wallet.store.structure.manager_user.nickname,
                        account_type=wallet.store.structure.manager_user.account_type,
                        school_id=wallet.store.structure.manager_user.school_id,
                    ),
                ),
                wallet_id=wallet.id,
            )
            if wallet.store
            else None,
            user=schemas_users.CoreUser(
                id=wallet.user.id,
                firstname=wallet.user.firstname,
                name=wallet.user.name,
                nickname=wallet.user.nickname,
                account_type=wallet.user.account_type,
                school_id=wallet.user.school_id,
                email=wallet.user.email,
            )
            if wallet.user
            else None,
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
    accepted_tos_signature: datetime,
    accepted_tos_version: int,
    db: AsyncSession,
) -> None:
    user_payment = models_myeclpay.UserPayment(
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
        update(models_myeclpay.UserPayment)
        .where(models_myeclpay.UserPayment.user_id == user_id)
        .values(
            accepted_tos_signature=accepted_tos_signature,
            accepted_tos_version=accepted_tos_version,
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
    transaction: schemas_myeclpay.Transaction,
    debited_wallet_device_id: UUID,
    store_note: str | None,
    db: AsyncSession,
) -> None:
    transaction_db = models_myeclpay.Transaction(
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
    )
    db.add(transaction_db)


async def update_transaction_status(
    transaction_id: UUID,
    status: TransactionStatus,
    db: AsyncSession,
) -> None:
    await db.execute(
        update(models_myeclpay.Transaction)
        .where(models_myeclpay.Transaction.id == transaction_id)
        .values(status=status),
    )


async def get_transaction(
    transaction_id: UUID,
    db: AsyncSession,
) -> schemas_myeclpay.Transaction | None:
    result = (
        (
            await db.execute(
                select(models_myeclpay.Transaction).where(
                    models_myeclpay.Transaction.id == transaction_id,
                ),
            )
        )
        .scalars()
        .first()
    )
    return (
        schemas_myeclpay.Transaction(
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
) -> Sequence[schemas_myeclpay.Transaction]:
    result = await db.execute(select(models_myeclpay.Transaction))
    return [
        schemas_myeclpay.Transaction(
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
) -> Sequence[models_myeclpay.Transaction]:
    result = await db.execute(
        select(models_myeclpay.Transaction)
        .where(
            or_(
                models_myeclpay.Transaction.debited_wallet_id == wallet_id,
                models_myeclpay.Transaction.credited_wallet_id == wallet_id,
            ),
        )
        .options(
            selectinload(models_myeclpay.Transaction.debited_wallet),
            selectinload(models_myeclpay.Transaction.credited_wallet),
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
            confirmed=transfer.confirmed,
        )
        for transfer in result.scalars().all()
    ]


async def create_transfer(
    transfer: schemas_myeclpay.Transfer,
    db: AsyncSession,
) -> None:
    transfer_db = models_myeclpay.Transfer(
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
        update(models_myeclpay.Transfer)
        .where(models_myeclpay.Transfer.id == transfer_id)
        .values(confirmed=True),
    )


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


async def get_transfer_by_transfer_identifier(
    db: AsyncSession,
    transfer_identifier: str,
) -> models_myeclpay.Transfer | None:
    result = await db.execute(
        select(models_myeclpay.Transfer).where(
            models_myeclpay.Transfer.transfer_identifier == transfer_identifier,
        ),
    )
    return result.scalars().first()


async def get_refunds(
    db: AsyncSession,
) -> Sequence[schemas_myeclpay.Refund]:
    result = await db.execute(select(models_myeclpay.Refund))
    return [
        schemas_myeclpay.Refund(
            id=refund.id,
            transaction_id=refund.transaction_id,
            credited_wallet_id=refund.credited_wallet_id,
            debited_wallet_id=refund.debited_wallet_id,
            total=refund.total,
            creation=refund.creation,
            seller_user_id=refund.seller_user_id,
            transaction=schemas_myeclpay.Transaction(
                id=refund.transaction.id,
                debited_wallet_id=refund.transaction.debited_wallet_id,
                credited_wallet_id=refund.transaction.credited_wallet_id,
                transaction_type=refund.transaction.transaction_type,
                seller_user_id=refund.transaction.seller_user_id,
                total=refund.transaction.total,
                creation=refund.transaction.creation,
                status=refund.transaction.status,
            ),
            debited_wallet=schemas_myeclpay.WalletInfo(
                id=refund.debited_wallet.id,
                type=refund.debited_wallet.type,
                owner_name=refund.debited_wallet.store.name
                if refund.debited_wallet.store
                else refund.debited_wallet.user.full_name
                if refund.debited_wallet.user
                else None,
            ),
            credited_wallet=schemas_myeclpay.WalletInfo(
                id=refund.credited_wallet.id,
                type=refund.credited_wallet.type,
                owner_name=refund.credited_wallet.store.name
                if refund.credited_wallet.store
                else refund.credited_wallet.user.full_name
                if refund.credited_wallet.user
                else None,
            ),
        )
        for refund in result.scalars().all()
    ]


async def create_refund(
    refund: schemas_myeclpay.RefundBase,
    db: AsyncSession,
) -> None:
    refund_db = models_myeclpay.Refund(
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
) -> schemas_myeclpay.Refund | None:
    result = (
        (
            await db.execute(
                select(models_myeclpay.Refund)
                .where(
                    models_myeclpay.Refund.transaction_id == transaction_id,
                )
                .options(
                    selectinload(models_myeclpay.Refund.debited_wallet),
                    selectinload(models_myeclpay.Refund.credited_wallet),
                ),
            )
        )
        .scalars()
        .first()
    )
    return (
        schemas_myeclpay.Refund(
            id=result.id,
            transaction_id=result.transaction_id,
            credited_wallet_id=result.credited_wallet_id,
            debited_wallet_id=result.debited_wallet_id,
            total=result.total,
            creation=result.creation,
            seller_user_id=result.seller_user_id,
            transaction=schemas_myeclpay.Transaction(
                id=result.transaction.id,
                debited_wallet_id=result.transaction.debited_wallet_id,
                credited_wallet_id=result.transaction.credited_wallet_id,
                transaction_type=result.transaction.transaction_type,
                seller_user_id=result.transaction.seller_user_id,
                total=result.transaction.total,
                creation=result.transaction.creation,
                status=result.transaction.status,
            ),
            debited_wallet=schemas_myeclpay.WalletInfo(
                id=result.debited_wallet.id,
                type=result.debited_wallet.type,
                owner_name=result.debited_wallet.store.name
                if result.debited_wallet.store
                else result.debited_wallet.user.full_name
                if result.debited_wallet.user
                else None,
            ),
            credited_wallet=schemas_myeclpay.WalletInfo(
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
) -> Sequence[schemas_myeclpay.Refund]:
    result = (
        (
            await db.execute(
                select(models_myeclpay.Refund).where(
                    or_(
                        models_myeclpay.Refund.debited_wallet_id == wallet_id,
                        models_myeclpay.Refund.credited_wallet_id == wallet_id,
                    ),
                ),
            )
        )
        .scalars()
        .all()
    )
    return [
        schemas_myeclpay.Refund(
            id=refund.id,
            transaction_id=refund.transaction_id,
            credited_wallet_id=refund.credited_wallet_id,
            debited_wallet_id=refund.debited_wallet_id,
            total=refund.total,
            creation=refund.creation,
            seller_user_id=refund.seller_user_id,
            transaction=schemas_myeclpay.Transaction(
                id=refund.transaction.id,
                debited_wallet_id=refund.transaction.debited_wallet_id,
                credited_wallet_id=refund.transaction.credited_wallet_id,
                transaction_type=refund.transaction.transaction_type,
                seller_user_id=refund.transaction.seller_user_id,
                total=refund.transaction.total,
                creation=refund.transaction.creation,
                status=refund.transaction.status,
            ),
            debited_wallet=schemas_myeclpay.WalletInfo(
                id=refund.debited_wallet.id,
                type=refund.debited_wallet.type,
                owner_name=refund.debited_wallet.store.name
                if refund.debited_wallet.store
                else refund.debited_wallet.user.full_name
                if refund.debited_wallet.user
                else None,
            ),
            credited_wallet=schemas_myeclpay.WalletInfo(
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


async def delete_used_qrcode(
    qr_code_id: UUID,
    db: AsyncSession,
) -> None:
    await db.execute(
        delete(models_myeclpay.UsedQRCode).where(
            models_myeclpay.UsedQRCode.qr_code_id == qr_code_id,
        ),
    )
