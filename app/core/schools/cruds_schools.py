"""File defining the functions called by the endpoints, making queries to the table using the models"""

from collections.abc import Sequence

from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core import models_core, schemas_core


async def get_schools(db: AsyncSession) -> Sequence[models_core.CoreSchool]:
    """Return all schools from database"""

    result = await db.execute(select(models_core.CoreSchool))
    return result.scalars().all()


async def get_school_by_id(
    db: AsyncSession,
    school_id: str,
) -> models_core.CoreSchool | None:
    """Return school with id from database"""
    result = await db.execute(
        select(models_core.CoreSchool)
        .where(models_core.CoreSchool.id == school_id)
        .options(
            selectinload(models_core.CoreSchool.students),
        ),  # needed to load the members from the relationship
    )
    return result.scalars().first()


async def get_school_by_name(
    db: AsyncSession,
    school_name: str,
) -> models_core.CoreSchool | None:
    """Return school with name from database"""
    result = await db.execute(
        select(models_core.CoreSchool)
        .where(models_core.CoreSchool.name == school_name)
        .options(
            selectinload(models_core.CoreSchool.students),
        ),  # needed to load the members from the relationship
    )
    return result.scalars().first()


async def create_school(
    school: models_core.CoreSchool,
    db: AsyncSession,
) -> models_core.CoreSchool:
    """Create a new school in database and return it"""

    db.add(school)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise
    else:
        return school


async def delete_school(db: AsyncSession, school_id: str):
    """Delete a school from database by id"""

    await db.execute(
        delete(models_core.CoreSchool).where(models_core.CoreSchool.id == school_id),
    )
    await db.commit()


async def update_school(
    db: AsyncSession,
    school_id: str,
    school_update: schemas_core.CoreSchoolUpdate,
):
    await db.execute(
        update(models_core.CoreSchool)
        .where(models_core.CoreSchool.id == school_id)
        .values(**school_update.model_dump(exclude_none=True)),
    )
    await db.commit()