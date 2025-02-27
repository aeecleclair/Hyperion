"""File defining the functions called by the endpoints, making queries to the table using the models"""

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.schools import models_schools, schemas_schools


async def get_schools(db: AsyncSession) -> Sequence[models_schools.CoreSchool]:
    """Return all schools from database"""

    result = await db.execute(select(models_schools.CoreSchool))
    return result.scalars().all()


async def get_school_by_id(
    db: AsyncSession,
    school_id: UUID,
) -> schemas_schools.CoreSchool | None:
    """Return school with id from database"""
    result = (
        (
            await db.execute(
                select(models_schools.CoreSchool).where(
                    models_schools.CoreSchool.id == school_id,
                ),
            )
        )
        .scalars()
        .first()
    )
    return (
        schemas_schools.CoreSchool(
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
) -> models_schools.CoreSchool | None:
    """Return school with name from database"""
    result = await db.execute(
        select(models_schools.CoreSchool).where(
            models_schools.CoreSchool.name == school_name,
        ),
    )
    return result.scalars().first()


async def create_school(
    school: models_schools.CoreSchool,
    db: AsyncSession,
) -> None:
    """Create a new school in database and return it"""

    db.add(school)


async def delete_school(db: AsyncSession, school_id: UUID):
    """Delete a school from database by id"""

    await db.execute(
        delete(models_schools.CoreSchool).where(
            models_schools.CoreSchool.id == school_id,
        ),
    )


async def update_school(
    db: AsyncSession,
    school_id: UUID,
    school_update: schemas_schools.CoreSchoolUpdate,
):
    await db.execute(
        update(models_schools.CoreSchool)
        .where(models_schools.CoreSchool.id == school_id)
        .values(**school_update.model_dump(exclude_none=True)),
    )
    await db.commit()
