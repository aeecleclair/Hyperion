import uuid
from collections.abc import Sequence

from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.models_core import CoreUser
from app.modules.greencode import models_greencode, schemas_greencode


async def get_items(db: AsyncSession) -> Sequence[models_greencode.GreenCodeItem]:
    result = await db.execute(
        select(models_greencode.GreenCodeItem).options(
            selectinload(models_greencode.GreenCodeItem.memberships).selectinload(
                models_greencode.GreenCodeMembership.user,
            ),
        ),
    )
    return result.scalars().all()


async def get_user_items(
    db: AsyncSession,
    user_id: str,
) -> Sequence[models_greencode.GreenCodeItem]:
    result = await db.execute(
        select(models_greencode.GreenCodeItem).where(
            models_greencode.GreenCodeItem.memberships.any(
                models_greencode.GreenCodeMembership.user_id == user_id,
            ),
        ),
    )
    return result.scalars().all()


async def get_item_by_qr_code_content(
    db: AsyncSession,
    qr_code_content: Sequence[str],
) -> models_greencode.GreenCodeItem | None:
    result = await db.execute(
        select(models_greencode.GreenCodeItem).where(
            models_greencode.GreenCodeItem.qr_code_content == qr_code_content,
        ),
    )
    return result.scalars().first()


async def get_item_by_id(
    db: AsyncSession,
    item_id: Sequence[str],
) -> models_greencode.GreenCodeItem | None:
    result = await db.execute(
        select(models_greencode.GreenCodeItem).where(
            models_greencode.GreenCodeItem.id == item_id,
        ),
    )
    return result.scalars().first()


async def create_item(
    item: models_greencode.GreenCodeItem,
    db: AsyncSession,
) -> models_greencode.GreenCodeItem:
    db.add(item)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise ValueError()
    return item


async def delete_item(item_id: str, db: AsyncSession):
    await db.execute(
        delete(models_greencode.GreenCodeItem).where(
            models_greencode.GreenCodeItem.id == item_id,
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
        update(models_greencode.GreenCodeItem)
        .where(models_greencode.GreenCodeItem.id == item_id)
        .values(**item_update.model_dump(exclude_none=True)),
    )
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise ValueError()


async def get_items_count(db: AsyncSession) -> int:
    result = await db.execute(select(models_greencode.GreenCodeItem.id))
    return len(result.scalars().all())


async def get_items_count_for_user(user_id: str, db: AsyncSession) -> int:
    result = await db.execute(
        select(models_greencode.GreenCodeMembership).where(
            models_greencode.GreenCodeMembership.user_id == user_id,
        ),
    )
    return len(result.scalars().all())


async def get_greencode_users(
    db: AsyncSession,
) -> list[CoreUser]:
    result = await db.execute(
        select(
            models_greencode.GreenCodeMembership,
        )
        .options(
            selectinload(models_greencode.GreenCodeMembership.user),
        )
        .group_by(models_greencode.GreenCodeMembership.user_id),  #
    )
    memberships = result.scalars().all()
    return [user_membership.user for user_membership in memberships]


async def create_membership(
    item_id: str,
    user_id: str,
    db: AsyncSession,
) -> models_greencode.GreenCodeMembership:
    membership = models_greencode.GreenCodeMembership(
        id=str(uuid.uuid4()),
        item_id=item_id,
        user_id=user_id,
    )
    db.add(membership)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise ValueError()
    return membership


async def delete_membership(item_id: str, user_id, db: AsyncSession):
    await db.execute(
        delete(models_greencode.GreenCodeMembership).where(
            models_greencode.GreenCodeMembership.user_id == user_id,
            models_greencode.GreenCodeMembership.item_id == item_id,
        ),
    )
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise ValueError()
