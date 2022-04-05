from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from ..models import models_core
from ..schemas import schemas_core

from sqlalchemy import select

# from sqlalchemy import delete


async def get_groups(db: AsyncSession):
    result = await db.execute(select(models_core.CoreGroup))
    return result.scalars().all()


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
        raise ValueError("Email already registered")
