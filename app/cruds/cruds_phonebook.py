# from sqlalchemy.orm import selectinload

import logging
from typing import Any, Callable, Coroutine

from fastapi import Depends, HTTPException
from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_request_id, get_user_from_token_with_scopes
from app.models import models_core, models_phonebook  # , models_core
from app.schemas import schemas_phonebook
from app.utils.tools import is_user_member_of_an_allowed_group
from app.utils.types import phonebook_types
from app.utils.types.groups_type import GroupType
from app.utils.types.scopes_type import ScopeType

# ---------------------------------------------------------------------------- #
#                               President test                                 #
# ---------------------------------------------------------------------------- #

hyperion_access_logger = logging.getLogger("hyperion.access")
hyperion_error_logger = logging.getLogger("hyperion.error")


def can_user_modify_association(
    association_id: str = None,
    db: AsyncSession = Depends(get_db),
) -> Callable[[models_core.CoreUser], Coroutine[Any, Any, models_core.CoreUser]]:
    """
    Generate a dependency which will:
        * check if the request header contains a valid API JWT token (a token that can be used to call endpoints from the API)
        * make sure the user making the request exists and is the president of the association with the given id
        * return the corresponding user `models_core.CoreUser` object
    """

    async def can_user_modify_association(
        user: models_core.CoreUser = Depends(
            get_user_from_token_with_scopes([[ScopeType.API]])
        ),
        request_id: str = Depends(get_request_id),
    ) -> models_core.CoreUser:
        """
        A dependency that checks that user is the president of the association with the given id then returns the corresponding user.
        """
        if is_user_member_of_an_allowed_group(
            user=user, allowed_groups=[GroupType.CAA, GroupType.BDE]
        ):
            # We know the user is a member of the group, we don't need to return an error and can return the CoreUser object
            return user

        if association_id is not None:
            memberships = get_memberships_by_association_id(association_id, db)
            for membership in memberships:
                if (
                    membership.user_id == user.id
                    and phonebook_types.RoleTags.president
                    in membership.role_tags.split(";")
                ):
                    return user

            hyperion_access_logger.warning(
                f"Can_user_modify_association: user is not authorized to modify the association {association_id} ({request_id})"
            )
            raise HTTPException(
                status_code=403,
                detail=f"Unauthorized, user is not authorized to modify the association {association_id}",
            )
        else:
            hyperion_access_logger.warning(
                f"Can_user_modify_association: user is not authorized to modify associations ({request_id})"
            )
            raise HTTPException(
                status_code=403,
                detail=f"Unauthorized, user is not authorized to modify associations {association_id}",
            )

    return can_user_modify_association


# ---------------------------------------------------------------------------- #
#                                    Get all                                   #
# ---------------------------------------------------------------------------- #
async def get_all_associations(
    db: AsyncSession,
) -> list[models_phonebook.Association] | None:
    """Return all associations from database"""

    result = await db.execute(select(models_phonebook.Association))
    return result.scalars().all()


async def get_all_role_tags(db: AsyncSession) -> list[str] | None:
    """Return all roles from database"""
    return [
        str(phonebook_types.RoleTags[el[0]])
        for el in list(phonebook_types.RoleTags.__members__.items())
    ]


async def get_all_kinds(db: AsyncSession) -> list[str] | None:
    """Return all kinds from database"""
    return [
        str(phonebook_types.Kinds[el[0]])
        for el in list(phonebook_types.Kinds.__members__.items())
    ]


async def get_all_memberships(
    mandate_year: int, db: AsyncSession
) -> list[models_phonebook.Membership] | None:
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
) -> list[models_phonebook.Membership] | None:
    """Return all memberships with id from database"""
    result = await db.execute(
        select(models_phonebook.Membership).where(
            models_phonebook.Membership.user_id == user_id
        )
    )
    return result.scalars().all()


async def get_memberships_by_association_id(
    association_id: str, db: AsyncSession
) -> list[models_phonebook.Membership] | None:
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
        raise


async def update_association(
    association: schemas_phonebook.AssociationEditComplete,
    db: AsyncSession,
):
    """Update an association in database"""
    await db.execute(
        update(models_phonebook.Association)
        .where(association.id == models_phonebook.Association.id)
        .values(**association.dict(exclude_none=True))
    )
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise


async def delete_association(association_id: str, db: AsyncSession):
    """Delete an association from database"""
    await db.execute(
        delete(models_phonebook.Association).where(
            association_id == models_phonebook.Association.id
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
        .where(membership_id == models_phonebook.Membership.id)
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
            membership_id == models_phonebook.Membership.id
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
    result = result.scalars().all()
    return [el.tag for el in result]


async def delete_role_tag(membership_id: str, db: AsyncSession):
    await db.execute(
        delete(models_phonebook.AttributedRoleTags).where(
            membership_id == models_phonebook.AttributedRoleTags.membership_id
        )
    )
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise
