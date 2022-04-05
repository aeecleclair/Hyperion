from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from ..models import models_core
from ..schemas import schemas_core
from sqlalchemy import select, delete


async def get_groups(db: AsyncSession):
    result = await db.execute(select(models_core.CoreGroup))
    return result.scalars().all()


async def get_group_by_id(db: AsyncSession, group_id: int):
    result = await db.execute(
        select(models_core.CoreGroup).where(models_core.CoreGroup.id == group_id)
    )
    return result.scalars().first()


async def create_group(group: schemas_core.CoreGroupCreate, db: AsyncSession):
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
    await db.execute(
        delete(models_core.CoreGroup).where(models_core.CoreGroup.id == group_id)
    )
    await db.commit()
