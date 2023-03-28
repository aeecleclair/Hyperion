# from sqlalchemy.orm import selectinload

from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import models_phonebook  # , models_core
from app.schemas import schemas_phonebook


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


async def get_association_by_id(
    db: AsyncSession, association_id: str
) -> models_phonebook.Association | None:
    """Return association with id from database"""
    result = await db.execute(
        select(models_phonebook.Association).where(
            models_phonebook.Association.id == association_id
        )
    )
    return result.scalars().first()


async def delete_association(association_id, db: AsyncSession):
    """Delete an association from database"""
    delete(models_phonebook.Association).where(
        association_id == models_phonebook.Association.id
    )
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise


async def update_association(association_id, association, db: AsyncSession):
    """Update an association in database"""
    update(models_phonebook.Association).where(
        association_id == models_phonebook.Association.id
    )
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise


async def create_role(role: schemas_phonebook.Role, db: AsyncSession):
    """Create a role in database"""
    db.add(role)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise
