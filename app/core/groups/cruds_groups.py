"""File defining the functions called by the endpoints, making queries to the table using the models"""

from collections.abc import Sequence

from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.groups import models_groups, schemas_groups


async def get_groups(db: AsyncSession) -> Sequence[models_groups.CoreGroup]:
    """Return all groups from database"""

    result = await db.execute(select(models_groups.CoreGroup))
    return result.scalars().all()


async def get_group_by_id(
    db: AsyncSession,
    group_id: str,
) -> models_groups.CoreGroup | None:
    """Return group with id from database"""
    result = await db.execute(
        select(models_groups.CoreGroup)
        .where(models_groups.CoreGroup.id == group_id)
        .options(
            selectinload(models_groups.CoreGroup.members),
        ),  # needed to load the members from the relationship
    )
    return result.scalars().first()


async def get_group_by_name(
    db: AsyncSession,
    group_name: str,
) -> models_groups.CoreGroup | None:
    """Return group with name from database"""
    result = await db.execute(
        select(models_groups.CoreGroup)
        .where(models_groups.CoreGroup.name == group_name)
        .options(
            selectinload(models_groups.CoreGroup.members),
        ),  # needed to load the members from the relationship
    )
    return result.scalars().first()


async def create_group(
    group: models_groups.CoreGroup,
    db: AsyncSession,
) -> models_groups.CoreGroup:
    """Create a new group in database and return it"""

    db.add(group)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise
    else:
        return group


async def delete_group(db: AsyncSession, group_id: str):
    """Delete a group from database by id"""

    await db.execute(
        delete(models_groups.CoreGroup).where(models_groups.CoreGroup.id == group_id),
    )
    await db.commit()


async def create_membership(
    membership: models_groups.CoreMembership,
    db: AsyncSession,
):
    """Add a user to a group using a membership"""

    db.add(membership)
    try:
        await db.commit()
        return await get_group_by_id(db, membership.group_id)
    except IntegrityError:
        await db.rollback()
        raise


async def delete_membership_by_group_id(
    group_id: str,
    db: AsyncSession,
):
    await db.execute(
        delete(models_groups.CoreMembership).where(
            models_groups.CoreMembership.group_id == group_id,
        ),
    )
    await db.commit()


async def delete_membership_by_group_and_user_id(
    group_id: str,
    user_id: str,
    db: AsyncSession,
):
    await db.execute(
        delete(models_groups.CoreMembership).where(
            models_groups.CoreMembership.group_id == group_id,
            models_groups.CoreMembership.user_id == user_id,
        ),
    )
    await db.commit()


async def update_group(
    db: AsyncSession,
    group_id: str,
    group_update: schemas_groups.CoreGroupUpdate,
):
    await db.execute(
        update(models_groups.CoreGroup)
        .where(models_groups.CoreGroup.id == group_id)
        .values(**group_update.model_dump(exclude_none=True)),
    )
    await db.commit()
