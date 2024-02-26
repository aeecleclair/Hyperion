# from sqlalchemy.orm import selectinload

from typing import Sequence

from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import models_core, models_phonebook  # , models_core
from app.schemas import schemas_phonebook
from app.utils.types import phonebook_types

# ---------------------------------------------------------------------------- #
#                               President test                                 #
# ---------------------------------------------------------------------------- #


async def is_user_president(
    association_id: str, user: models_core.CoreUser, db: AsyncSession
) -> bool:

    if association_id is not None:
        memberships = await get_memberships_by_association_id(association_id, db)
        if memberships is None:
            return False

        for membership in memberships:
            if (
                membership.user_id == user.id
                and phonebook_types.RoleTags.president
                in membership.role_tags.split(";")
            ):
                return True
    return False


# ---------------------------------------------------------------------------- #
#                                    Get all                                   #
# ---------------------------------------------------------------------------- #
async def get_all_associations(
    db: AsyncSession,
) -> Sequence[models_phonebook.Association] | None:
    """Return all associations from database"""

    result = await db.execute(select(models_phonebook.Association))
    return result.scalars().all()


async def get_all_role_tags(db: AsyncSession) -> Sequence[str] | None:
    """Return all roles from database"""
    return [
        str(phonebook_types.RoleTags[el[0]])
        for el in list(phonebook_types.RoleTags.__members__.items())
    ]


async def get_all_kinds(db: AsyncSession) -> Sequence[str] | None:
    """Return all kinds from database"""
    return [
        str(phonebook_types.Kinds[el[0]])
        for el in list(phonebook_types.Kinds.__members__.items())
    ]


async def get_all_memberships(
    mandate_year: int, db: AsyncSession
) -> Sequence[models_phonebook.Membership] | None:
    """Return all memberships from database"""

    result = await db.execute(
        select(models_phonebook.Membership).where(
            models_phonebook.Membership.mandate_year == mandate_year
        )
    )
    return result.scalars().all()


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


async def get_member_by_id(
    member_id: str, db: AsyncSession
) -> models_core.CoreUser | None:
    """Return member with id from database"""
    result = await db.execute(
        select(models_core.CoreUser).where(models_core.CoreUser.id == member_id)
    )
    return result.scalars().first()


async def get_membership_by_user_id(
    user_id: str, db: AsyncSession
) -> Sequence[models_phonebook.Membership] | None:
    """Return all memberships with id from database"""
    result = await db.execute(
        select(models_phonebook.Membership).where(
            models_phonebook.Membership.user_id == user_id
        )
    )
    return result.scalars().all()


async def get_memberships_by_association_id(
    association_id: str, db: AsyncSession
) -> Sequence[models_phonebook.Membership] | None:
    """Return all memberships with id from database"""
    result = await db.execute(
        select(models_phonebook.Membership).where(
            models_phonebook.Membership.association_id == association_id
        )
    )
    return result.scalars().all()


async def get_membership_by_id(
    membership_id: str, db: AsyncSession
) -> models_phonebook.Membership | None:
    """Return the membership with id from database"""
    result = await db.execute(
        select(models_phonebook.Membership).where(
            models_phonebook.Membership.id == membership_id
        )
    )
    return result.scalars().first()


# ---------------------------------------------------------------------------- #
#                                  Association  OK                             #
# ---------------------------------------------------------------------------- #
async def create_association(
    association: models_phonebook.Association, db: AsyncSession
):
    """Create a new association in database and return it"""
    db.add(association)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
    return association


async def update_association(
    association: schemas_phonebook.AssociationEditComplete,
    db: AsyncSession,
):
    """Update an association in database"""
    await db.execute(
        update(models_phonebook.Association)
        .where(models_phonebook.Association.id == association.id)
        .values(**association.dict(exclude_none=True))
    )
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise


async def delete_association(association_id: str, db: AsyncSession):
    """Delete an association from database"""
    await db.execute(  # Memberships from the association must first be deleted
        delete(models_phonebook.Membership).where(
            models_phonebook.Membership.association_id == association_id
        )
    )
    await db.execute(
        delete(models_phonebook.Association).where(
            models_phonebook.Association.id == association_id
        )
    )
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise


# ---------------------------------------------------------------------------- #
#                                  Membership                                  #
# ---------------------------------------------------------------------------- #
async def create_membership(membership: models_phonebook.Membership, db: AsyncSession):
    """Create a membership in database"""
    db.add(membership)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise


async def update_membership(
    membership: schemas_phonebook.MembershipEdit, membership_id: str, db: AsyncSession
):
    """Update a membership in database"""
    await db.execute(
        update(models_phonebook.Membership)
        .where(models_phonebook.Membership.id == membership_id)
        .values(**membership.dict(exclude_none=True))
    )
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise


async def delete_membership(membership_id: str, db: AsyncSession):
    """Delete a membership in database"""
    await db.execute(
        delete(models_phonebook.Membership).where(
            models_phonebook.Membership.id == membership_id
        )
    )
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise


# ---------------------------------------------------------------------------- #
#                                   RoleTags                                   #
# ---------------------------------------------------------------------------- #
async def add_new_role(role_tag: str, id: str, db: AsyncSession):
    role = models_phonebook.AttributedRoleTags(membership_id=id, tag=role_tag)
    db.add(role)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise


async def delete_role(role_tag: str, id: str, db: AsyncSession):
    await db.execute(
        delete(models_phonebook.AttributedRoleTags).where(
            models_phonebook.AttributedRoleTags.membership_id == id
            and models_phonebook.AttributedRoleTags.tag == role_tag
        )
    )
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise


async def get_membership_roletags(membership_id: str, db: AsyncSession):
    result = await db.execute(
        select(models_phonebook.AttributedRoleTags).where(
            models_phonebook.AttributedRoleTags.membership_id == membership_id
        )
    )

    return [el.tag for el in result.scalars().all()]


async def delete_role_tag(membership_id: str, db: AsyncSession):
    await db.execute(
        delete(models_phonebook.AttributedRoleTags).where(
            models_phonebook.AttributedRoleTags.membership_id == membership_id
        )
    )
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise
