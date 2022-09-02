"""File defining the functions called by the endpoints, making queries to the table using the models"""

from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import models_music


async def get_musicians(db: AsyncSession) -> list[models_music.Musicians]:
    """Return all musicians from database"""

    result = await db.execute(select(models_music.Musicians))
    return result.scalars().all()


async def get_musician_by_id(
    db: AsyncSession, user_id: str
) -> models_music.Musicians | None:
    """Return musician with id from database as a dictionary"""

    result = await db.execute(
        select(models_music.Musicians)
        .where(models_music.Musicians.user_id == user_id)
        .options(
            # The user relationship need to be loaded
            selectinload(models_music.Musicians.user)
        )
    )
    return result.scalars().first()


async def create_musician(
    db: AsyncSession, musician: models_music.Musicians
) -> models_music.Musicians:
    """
    Create a new musician in the database
    """
    try:
        db.add(musician)
        await db.commit()
        return musician
    except IntegrityError:
        await db.rollback()
        return None


async def update_musician(db: AsyncSession, user_id: str, musician_update):
    await db.execute(
        update(models_music.Musicians)
        .where(models_music.Musicians.user_id == user_id)
        .values(**musician_update.dict(exclude_none=True))
    )
    await db.commit()


async def delete_musician(db: AsyncSession, user_id: str):
    await db.execute(
        delete(models_music.Musicians).where(models_music.Musicians.user_id == user_id)
    )
    await db.commit()
