"""File defining the functions called by the endpoints, making queries to the table using the models"""

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import models_core
from app.schemas import schemas_core


async def get_groups(db: AsyncSession) -> list[models_core.CoreGroup]:
    """Return all groups from database"""

    result = await db.execute(select(models_core.CoreGroup))
    return result.scalars().all()


async def get_group_by_id(db: AsyncSession, group_id: int) -> models_core.CoreGroup:
    """Return group with id from database"""
    result = await db.execute(
        select(models_core.CoreGroup)
        .where(models_core.CoreGroup.id == group_id)
        .options(
            selectinload(models_core.CoreGroup.members)
        )  # needed to load the members from the relationship
    )
    return result.scalars().first()


async def create_group(
    group: schemas_core.CoreGroupCreate, db: AsyncSession
) -> models_core.CoreGroup:
    """Create a new group in database and return it"""

    db_group = models_core.CoreGroup(
        name=group.name,
        description=group.description,
    )
    db.add(db_group)
    try:
        await db.commit()
        return db_group
    except IntegrityError:
        await db.rollback()
        raise ValueError("This name is already used")


async def delete_group(db: AsyncSession, group_id: int):
    """Delete a group from database by id"""

    await db.execute(
        delete(models_core.CoreGroup).where(models_core.CoreGroup.id == group_id)
    )
    await db.commit()
