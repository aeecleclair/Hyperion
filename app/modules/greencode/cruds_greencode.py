import uuid
from collections.abc import Sequence

from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.models_core import CoreUser
from app.modules.greencode import models_greencode, schemas_greencode


async def get_items(db: AsyncSession) -> Sequence[models_greencode.GreenCodeItem]:
    """Return all items."""
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
    """ "Return all items for a user_id."""

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
    """Return an item by qr code content."""
    result = await db.execute(
        select(models_greencode.GreenCodeItem).where(
            models_greencode.GreenCodeItem.qr_code_content == qr_code_content,
        ),
    )
    return result.scalars().first()


async def get_item_by_id(
    db: AsyncSession,
    item_id: uuid.UUID,
) -> models_greencode.GreenCodeItem | None:
    """Return an item by item_id."""
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
    """Create an item."""
    db.add(item)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise ValueError()
    return item


async def delete_item(item_id: uuid.UUID, db: AsyncSession):
    """Delete an item."""
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
    item_id: uuid.UUID,
    item_update: schemas_greencode.ItemUpdate,
    db: AsyncSession,
):
    """Update an item."""
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
    """Return the total number of items."""
    result = await db.execute(select(models_greencode.GreenCodeItem.id))
    return len(result.scalars().all())


async def get_items_count_for_user(user_id: str, db: AsyncSession) -> int:
    """Return the total number of items discovered by a user by user_id."""
    result = await db.execute(
        select(models_greencode.GreenCodeMembership).where(
            models_greencode.GreenCodeMembership.user_id == user_id,
        ),
    )
    return len(result.scalars().all())


async def get_greencode_users(
    db: AsyncSession,
) -> list[CoreUser]:
    """Return all users who have discovered at least an item."""
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
    item_id: uuid.UUID,
    user_id: str,
    db: AsyncSession,
) -> models_greencode.GreenCodeMembership:
    """Create a membership. Make user_id discover item_id."""
    membership = models_greencode.GreenCodeMembership(
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


async def delete_membership(item_id: uuid.UUID, user_id, db: AsyncSession):
    """Delete a membership. Make user_id undiscover item_id."""
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
