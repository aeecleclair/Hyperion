"""File defining the functions called by the endpoints, making queries to the table using the models"""

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.core_endpoints import models_core, schemas_core


async def get_schools(db: AsyncSession) -> Sequence[models_core.CoreSchool]:
    """Return all schools from database"""

    result = await db.execute(select(models_core.CoreSchool))
    return result.scalars().all()


async def get_school_by_id(
    db: AsyncSession,
    school_id: UUID,
) -> schemas_core.CoreSchool | None:
    """Return school with id from database"""
    result = (
        (
            await db.execute(
                select(models_core.CoreSchool).where(
                    models_core.CoreSchool.id == school_id,
                ),
            )
        )
        .scalars()
        .first()
    )
    return (
        schemas_core.CoreSchool(
            name=result.name,
            email_regex=result.email_regex,
            id=result.id,
        )
        if result
        else None
    )


async def get_school_by_name(
    db: AsyncSession,
    school_name: str,
) -> models_core.CoreSchool | None:
    """Return school with name from database"""
    result = await db.execute(
        select(models_core.CoreSchool).where(
            models_core.CoreSchool.name == school_name,
        ),
    )
    return result.scalars().first()


async def create_school(
    school: models_core.CoreSchool,
    db: AsyncSession,
) -> None:
    """Create a new school in database and return it"""

    db.add(school)


async def delete_school(db: AsyncSession, school_id: UUID):
    """Delete a school from database by id"""

    await db.execute(
        delete(models_core.CoreSchool).where(models_core.CoreSchool.id == school_id),
    )


async def update_school(
    db: AsyncSession,
    school_id: UUID,
    school_update: schemas_core.CoreSchoolUpdate,
):
    await db.execute(
        update(models_core.CoreSchool)
        .where(models_core.CoreSchool.id == school_id)
        .values(**school_update.model_dump(exclude_none=True)),
    )
    await db.commit()
