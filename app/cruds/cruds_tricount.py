from typing import Sequence

from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import models_core, models_tricount
from app.schemas import schemas_tricount


async def create_sharer_group(
    sharer_group: models_tricount.SharerGroup,
    db: AsyncSession,
) -> models_tricount.SharerGroup:
    db.add(sharer_group)
    try:
        await db.commit()
        return sharer_group
    except IntegrityError as error:
        await db.rollback()
        raise ValueError(error)


async def get_sharer_groups_by_user_id(
    user_id: str,
    db: AsyncSession,
) -> Sequence[models_tricount.SharerGroup]:
    """
    TODO: remove
    """
    result = await db.execute(
        select(models_tricount.SharerGroup).where(
            models_tricount.SharerGroup.members.any(models_core.CoreUser.id == user_id)
        )
    )

    return result.scalars().all()


async def get_sharer_groups_by_id(
    sharer_group_id: str,
    db: AsyncSession,
) -> models_tricount.SharerGroup | None:
    result = await db.execute(
        select(models_tricount.SharerGroup)
        .where(models_tricount.SharerGroup.id == sharer_group_id)
        .options(
            selectinload(
                models_tricount.SharerGroup.members,
            ),
            selectinload(
                models_tricount.SharerGroup.transactions,
            ),
        )
    )

    return result.scalars().first()


async def get_sharer_group_memberships_by_user_id(
    user_id: str,
    db: AsyncSession,
) -> Sequence[models_tricount.SharerGroupMembership]:
    result = await db.execute(
        select(models_tricount.SharerGroupMembership)
        .where(models_tricount.SharerGroupMembership.user_id == user_id)
        .order_by(models_tricount.SharerGroupMembership.position.desc())
    )

    return result.scalars().all()


async def update_sharer_group(
    db: AsyncSession,
    sharer_group_id: str,
    sharer_group_update: schemas_tricount.SharerGroupUpdate,
) -> None:
    await db.execute(
        update(models_tricount.SharerGroup)
        .where(models_tricount.SharerGroup.id == sharer_group_id)
        .values(**sharer_group_update.dict(exclude_none=True))
    )
    await db.commit()


async def get_sharer_group_membership_by_user_id_and_group_id(
    user_id: str,
    sharer_group_id: str,
    db: AsyncSession,
) -> models_tricount.SharerGroupMembership | None:
    result = await db.execute(
        select(models_tricount.SharerGroupMembership).where(
            models_tricount.SharerGroupMembership.user_id == user_id,
            models_tricount.SharerGroupMembership.sharer_group_id == sharer_group_id,
        )
    )

    return result.scalars().first()


async def create_sharer_group_membership(
    sharer_group_membership: models_tricount.SharerGroupMembership,
    db: AsyncSession,
) -> None:
    db.add(sharer_group_membership)
    try:
        await db.commit()
    except IntegrityError as error:
        await db.rollback()
        raise ValueError(error)


async def update_sharer_group_membership_active_status(
    db: AsyncSession,
    sharer_group_id: str,
    user_id: str,
    active: bool,
) -> None:
    await db.execute(
        update(models_tricount.SharerGroupMembership)
        .where(
            models_tricount.SharerGroupMembership.user_id == user_id,
            models_tricount.SharerGroupMembership.sharer_group_id == sharer_group_id,
        )
        .values(
            {
                "active": active,
            }
        )
    )
    await db.commit()


#


async def get_allowed_groups_by_root(
    root: str,
    db: AsyncSession,
) -> Sequence[str]:
    """Return the every module with their visibility"""

    result = await db.execute(
        select(
            models_core.ModuleVisibility.allowed_group_id,
        ).where(models_core.ModuleVisibility.root == root)
    )

    resultList = result.unique().scalars().all()

    return resultList


async def get_module_visibility(
    root: str,
    group_id: str,
    db: AsyncSession,
) -> models_core.ModuleVisibility | None:
    """Return module visibility by root and group id"""

    result = await db.execute(
        select(models_core.ModuleVisibility).where(
            models_core.ModuleVisibility.allowed_group_id == group_id,
            models_core.ModuleVisibility.root == root,
        )
    )
    return result.unique().scalars().first()


async def create_module_visibility(
    module_visibility: models_core.ModuleVisibility,
    db: AsyncSession,
) -> models_core.ModuleVisibility:
    """Create a new module visibility in database and return it"""

    db.add(module_visibility)
    try:
        await db.commit()
        return module_visibility
    except IntegrityError as error:
        await db.rollback()
        raise ValueError(error)


async def delete_module_visibility(
    root: str,
    allowed_group_id: str,
    db: AsyncSession,
):
    await db.execute(
        delete(models_core.ModuleVisibility).where(
            models_core.ModuleVisibility.root == root,
            models_core.ModuleVisibility.allowed_group_id == allowed_group_id,
        )
    )
    await db.commit()


async def create_transaction(
    transaction: models_tricount.Transaction,
    db: AsyncSession,
) -> None:
    db.add(transaction)
    try:
        await db.commit()
    except IntegrityError as error:
        await db.rollback()
        raise ValueError(error)


async def create_transaction_beneficiary(
    transaction_beneficiary: models_tricount.TransactionBeneficiariesMembership,
    db: AsyncSession,
) -> None:
    db.add(transaction_beneficiary)
    try:
        await db.commit()
    except IntegrityError as error:
        await db.rollback()
        raise ValueError(error)


async def get_transaction_by_id(
    transaction_id: str,
    db: AsyncSession,
) -> models_tricount.Transaction | None:
    result = await db.execute(
        select(models_tricount.Transaction).where(
            models_tricount.Transaction.id == transaction_id,
        )
    )

    return result.scalars().first()


async def update_transaction(
    transaction_update: schemas_tricount.TransactionUpdateBase,
    transaction_id: str,
    db: AsyncSession,
) -> models_tricount.Transaction | None:
    result = await db.execute(
        update(models_tricount.Transaction)
        .where(
            models_tricount.Transaction.id == transaction_id,
        )
        .values(**transaction_update.dict(exclude_none=True))
    )

    return result.scalars().first()


async def delete_transaction_beneficiaries(
    transaction_id: str,
    db: AsyncSession,
) -> None:
    await db.execute(
        delete(models_tricount.TransactionBeneficiariesMembership).where(
            models_tricount.TransactionBeneficiariesMembership.transaction_id
            == transaction_id,
        )
    )


async def delete_transaction(
    transaction_id: str,
    db: AsyncSession,
) -> None:
    await db.execute(
        delete(models_tricount.Transaction).where(
            models_tricount.Transaction.id == transaction_id,
        )
    )
    await db.commit()
