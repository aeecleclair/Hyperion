# from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from ..models import models_core

# from ..schemas import schemas_core
from sqlalchemy import select

# from sqlalchemy import delete


async def get_groups(db: AsyncSession):
    result = await db.execute(select(models_core.CoreGroup))
    return result.scalars().all()
