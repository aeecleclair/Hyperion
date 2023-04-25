# from sqlalchemy.orm import selectinload

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import models_core, models_phonebook  # , models_core
from app.schemas import schemas_phonebook


# ---------------------------------------------------------------------------- #
#                                    Get all                                   #
# ---------------------------------------------------------------------------- #
async def get_all_associations(
    db: AsyncSession,
) -> list[models_core.CoreGroup] | None:
    """Return all associations from database"""  # REVIEW - ready to be tested

    result = await db.execute(
        select(models_core.CoreGroup).where(
            models_core.CoreGroup.group_type is not None
        )
    )
    return result.scalars().all()


async def get_all_role_tags(db: AsyncSession) -> list[models_phonebook.RoleTags] | None:
    """Return all role tags from database"""  # REVIEW - ready to be tested
    result = await db.execute(select(models_phonebook.RoleTags))
    return result.scalars().all()


async def get_all_memberships(
    db: AsyncSession,
) -> list[models_phonebook.Membership] | None:
    """Return all memberships from database"""  # REVIEW - ready to be tested

    result = await db.execute(select(models_phonebook.Membership))
    return result.scalars().all()


# ---------------------------------------------------------------------------- #
#                                   Get by <param>                             #
# ---------------------------------------------------------------------------- #
async def get_membership_by_user_id(
    user_id: str, db: AsyncSession
) -> list[models_phonebook.Membership] | None:
    """Return all associations with user_id from database"""
    result = await db.execute(
        select(models_phonebook.Membership).where(
            models_phonebook.Membership.user_id == user_id
        )
    )
    return result.scalars().all()


# ---------------------------------------------------------------------------- #
#                                  Get By X ID                                 # # REVIEW - ready to be tested
# ---------------------------------------------------------------------------- #
async def get_association_by_id(
    association_id: str, db: AsyncSession
) -> models_core.CoreGroup | None:
    """Return association with id from database"""
    result = await db.execute(
        select(models_core.CoreGroup).where(models_core.CoreGroup.id == association_id)
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


async def get_mbmrships_by_association_id(
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
#                                  Membership                                  # #REVIEW - ready to be tested
# ---------------------------------------------------------------------------- #
async def create_membership(membership: models_phonebook.Membership, db: AsyncSession):
    """Create a membership in database"""
    db.add(membership)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise


async def delete_membership(
    membership: schemas_phonebook.MembershipBase, db: AsyncSession
):
    """Delete a membership in database"""
    delete(models_phonebook.Membership).where(
        membership.association_id == models_phonebook.Membership.association_id
        and membership.user_id == models_phonebook.Membership.user_id
    )
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise
