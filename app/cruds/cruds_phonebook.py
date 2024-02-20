# from sqlalchemy.orm import selectinload

from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import models_phonebook  # , models_core
from app.schemas import schemas_phonebook


# ---------------------------------------------------------------------------- #
#                                    Get all                                   #
# ---------------------------------------------------------------------------- #
async def get_all_associations(
    db: AsyncSession,
) -> list[models_phonebook.Association] | None:
    """Return all associations from database"""

    result = await db.execute(select(models_phonebook.Association))
    return result.scalars().all()


async def get_all_roles(db: AsyncSession) -> list[models_phonebook.Role] | None:
    """Return all roles from database"""
    result = await db.execute(select(models_phonebook.Role))
    return result.scalars().all()


async def get_all_memberships(
    db: AsyncSession,
) -> list[models_phonebook.Membership] | None:
    """Return all memberships from database"""

    result = await db.execute(select(models_phonebook.Membership))
    return result.scalars().all()


# ---------------------------------------------------------------------------- #
#                                   Get by <param>                             #
# ---------------------------------------------------------------------------- #


# ---------------------------------------------------------------------------- #
#                                  Get By X ID                                 #
# ---------------------------------------------------------------------------- #
async def get_association_by_id(
    association_id: str, db: AsyncSession
) -> models_phonebook.Association | None:
    """Return association with id from database"""
    result = await db.execute(
        select(models_phonebook.Association).where(
            models_phonebook.Association.id == association_id
        )
    )
    return result.scalars().first()


async def get_role_by_id(
    role_id: str, db: AsyncSession
) -> models_phonebook.Role | None:
    """Return role with id from database"""
    result = await db.execute(
        select(models_phonebook.Role).where(models_phonebook.Role.id == role_id)
    )
    return result.scalars().first()


async def get_mbrship_by_user_id(
    user_id: str, db: AsyncSession
) -> list[models_phonebook.Membership] | None:
    """Return all memberships with id from database"""
    result = await db.execute(
        select(models_phonebook.Membership).where(
            models_phonebook.Membership.user_id == user_id
        )
    )
    return result.scalars().all()


async def get_mbmrships_by_association(
    association_id: str, db: AsyncSession
) -> list[models_phonebook.Membership] | None:
    """Return all memberships with id from database"""
    result = await db.execute(
        select(models_phonebook.Membership).where(
            models_phonebook.Membership.association_id == association_id
        )
    )
    return result.scalars().all()


# ---------------------------------------------------------------------------- #
#                                  Association  OK                             #
# ---------------------------------------------------------------------------- #
async def create_association(
    association: schemas_phonebook.AssociationComplete, db: AsyncSession
):
    """Create a new association in database and return it"""
    db.add(association)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise


async def update_association(
    association_id: str,
    association: schemas_phonebook.AssociationBase,
    db: AsyncSession,
):
    """Update an association in database"""
    update(models_phonebook.Association).where(
        association_id == models_phonebook.Association.id
    ).values(**association.dict(exclude_none=True))
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise


async def delete_association(association_id: str, db: AsyncSession):
    """Delete an association from database"""
    delete(models_phonebook.Association).where(
        association_id == models_phonebook.Association.id
    )
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise


# ---------------------------------------------------------------------------- #
#                                     Role OK                                  #
# ---------------------------------------------------------------------------- #
async def create_role(role: schemas_phonebook.RoleComplete, db: AsyncSession):
    """Create a role in database"""
    db.add(role)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise


async def update_role(role: schemas_phonebook.RoleComplete, db: AsyncSession):
    """Update a role in database"""
    update(models_phonebook.Role).where(role.id == models_phonebook.Role.id).values(
        **role.dict(exclude_none=True)
    )
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise


async def delete_role(role_id: str, db: AsyncSession):
    """Delete a role in database"""
    delete(models_phonebook.Role).where(role_id == models_phonebook.Role.id)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise


# ---------------------------------------------------------------------------- #
#                                  Membership                                  #
# ---------------------------------------------------------------------------- #
async def create_membership(
    membership: schemas_phonebook.MembershipComplete, db: AsyncSession
):
    """Create a membership in database"""
    db.add(membership)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise


async def update_membership(
    membership_id: str,
    membership: schemas_phonebook.MembershipBase,
    db: AsyncSession,
):
    """Update a membership in database"""
    update(models_phonebook.Membership).where(
        membership_id == models_phonebook.Membership.id
    ).values(**membership.dict(exclude_none=True))
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise


async def delete_membership(membership_id: str, db: AsyncSession):
    """Delete a membership in database"""
    delete(models_phonebook.Membership).where(
        membership_id == models_phonebook.Membership.id
    )
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise
