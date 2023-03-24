from sqlalchemy import select  # , delete, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import models_phonebook  # , models_core

# from sqlalchemy.orm import selectinload


# from app.schemas import schemas_core


async def get_associations(db: AsyncSession) -> list[models_phonebook.Association]:
    """Return all associations from database"""

    result = await db.execute(select(models_phonebook.Association))
    return result.scalars().all()


async def get_associations_by_query(
    query: str, db: AsyncSession
) -> list[models_phonebook.Association]:
    """Return all associations from database"""

    result = await db.execute(
        select(models_phonebook.Association).where(
            models_phonebook.Association.type.like(f"%{query}%")
        )
    )
    return result.scalars().all()


async def create_association(association, db: AsyncSession):
    """Create a new association in database and return it"""

    db.add(association)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise
