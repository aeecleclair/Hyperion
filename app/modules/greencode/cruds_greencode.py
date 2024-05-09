from collections.abc import Sequence

from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models_core import CoreUser
from app.modules.greencode import models_greencode, schemas_greencode


async def get_items(db: AsyncSession) -> Sequence[models_greencode.Item]:
    result = await db.execute(select(models_greencode.Item))
    return result.scalars().all()


async def get_user_items(
    db: AsyncSession,
    user_id: str,
) -> Sequence[models_greencode.Item]:
    result = await db.execute(
        select(models_greencode.Item).where(
            models_greencode.Item.users.any(
                models_greencode.Membership.user_id == user_id,
            ),
        ),
    )
    return result.scalars().all()


async def get_item_by_qr_code_content(
    db: AsyncSession,
    qr_code_content: Sequence[str],
) -> models_greencode.Item | None:
    result = await db.execute(
        select(models_greencode.Item).where(
            models_greencode.Item.qr_code_content == qr_code_content,
        ),
    )
    return result.scalars().first()


async def get_item_by_id(
    db: AsyncSession,
    item_id: Sequence[str],
) -> models_greencode.Item | None:
    result = await db.execute(
        select(models_greencode.Item).where(
            models_greencode.Item.id == item_id,
        ),
    )
    return result.scalars().first()


async def create_item(
    item: models_greencode.Item,
    db: AsyncSession,
) -> models_greencode.Item:
    db.add(item)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise ValueError()
    return item


async def delete_item(item_id: str, db: AsyncSession):
    await db.execute(
        delete(models_greencode.Item).where(
            models_greencode.Item.id == item_id,
        ),
    )
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise ValueError()


async def update_item(
    item_id: str,
    item_update: schemas_greencode.ItemUpdate,
    db: AsyncSession,
):
    await db.execute(
        update(models_greencode.Item)
        .where(models_greencode.Item.id == item_id)
        .values(**item_update.model_dump(exclude_none=True)),
    )
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise ValueError()


async def get_items_count(db: AsyncSession) -> int | None:
    result = await db.execute(select(func.count(models_greencode.Item)))
    return result.scalars().first()


async def get_items_count_for_user(user_id: str, db: AsyncSession) -> int | None:
    result = await db.execute(
        select(func.count(models_greencode.Membership)).where(
            models_greencode.Membership.user_id == user_id,
        ),
    )
    return result.scalars().first()


async def get_items_count_for_users(
    user_id: str,
    db: AsyncSession,
) -> Sequence[tuple[CoreUser, int]]:
    result = await db.execute(
        select(
            models_greencode.Membership.user,
            func.count(models_greencode.Membership),
        ).where(
            models_greencode.Membership.user_id == user_id,
        ),
    )
    return result.scalars().all()


async def create_membership(
    membership: models_greencode.Membership,
    db: AsyncSession,
) -> models_greencode.Membership:
    db.add(membership)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise ValueError()
    return membership


async def delete_membership(membership_id: str, db: AsyncSession):
    await db.execute(
        delete(models_greencode.Membership).where(
            models_greencode.Membership.id == membership_id,
        ),
    )
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise ValueError()
