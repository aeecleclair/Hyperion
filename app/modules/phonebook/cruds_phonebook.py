from collections.abc import Sequence

from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import models_core
from app.modules.phonebook import models_phonebook, schemas_phonebook, types_phonebook


# ---------------------------------------------------------------------------- #
#                               President test                                 #
# ---------------------------------------------------------------------------- #
async def is_user_president(
    association_id: str,
    user: models_core.CoreUser,
    db: AsyncSession,
) -> bool:
    association = await get_association_by_id(association_id=association_id, db=db)
    if association is None:
        return False

    membership = await get_membership_by_association_id_user_id_and_mandate_year(
        association_id=association_id,
        user_id=user.id,
        mandate_year=association.mandate_year,
        db=db,
    )
    return (
        membership is not None
        and types_phonebook.RoleTags.president.value in membership.role_tags.split(";")
    )


# ---------------------------------------------------------------------------- #
#                                    Get all                                   #
# ---------------------------------------------------------------------------- #
async def get_all_associations(
    db: AsyncSession,
) -> Sequence[models_phonebook.Association]:
    """Return all Associations from database"""

    result = await db.execute(select(models_phonebook.Association))
    return result.scalars().all()


async def get_all_role_tags() -> Sequence[str]:
    """Return all RoleTags from Enum"""

    return [tag.value for tag in types_phonebook.RoleTags]


async def get_all_kinds() -> Sequence[str]:
    """Return all Kinds from Enum"""

    return [kind.value for kind in types_phonebook.Kinds]


async def get_all_memberships(
    mandate_year: int,
    db: AsyncSession,
) -> Sequence[models_phonebook.Membership]:
    """Return all Memberships from database"""

    result = await db.execute(
        select(models_phonebook.Membership).where(
            models_phonebook.Membership.mandate_year == mandate_year,
        ),
    )
    return result.scalars().all()


# ---------------------------------------------------------------------------- #
#                                  Association                                 #
# ---------------------------------------------------------------------------- #
async def create_association(
    association: models_phonebook.Association,
    db: AsyncSession,
) -> models_phonebook.Association:
    """Create a new Association in database and return it"""

    db.add(association)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
    return association


async def update_association(
    association_id: str,
    association_edit: schemas_phonebook.AssociationEdit,
    db: AsyncSession,
):
    """Update an Association in database"""

    await db.execute(
        update(models_phonebook.Association)
        .where(models_phonebook.Association.id == association_id)
        .values(**association_edit.model_dump(exclude_none=True)),
    )
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise


async def delete_association(association_id: str, db: AsyncSession):
    """Delete an Association from database"""

    await db.execute(  # Memberships from the Association must be deleted first
        delete(models_phonebook.Membership).where(
            models_phonebook.Membership.association_id == association_id,
        ),
    )
    await db.execute(
        delete(models_phonebook.Association).where(
            models_phonebook.Association.id == association_id,
        ),
    )
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise


async def get_association_by_id(
    association_id: str,
    db: AsyncSession,
) -> models_phonebook.Association | None:
    """Return Association with id from database"""

    result = await db.execute(
        select(models_phonebook.Association).where(
            models_phonebook.Association.id == association_id,
        ),
    )
    return result.scalars().first()


# ---------------------------------------------------------------------------- #
#                                  Membership                                  #
# ---------------------------------------------------------------------------- #
async def create_membership(membership: models_phonebook.Membership, db: AsyncSession):
    """Create a Membership in database"""
    db.add(membership)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise


async def update_membership(
    membership_edit: schemas_phonebook.MembershipEdit,
    membership_id: str,
    db: AsyncSession,
):
    """Update a Membership in database"""

    await db.execute(
        update(models_phonebook.Membership)
        .where(models_phonebook.Membership.id == membership_id)
        .values(**membership_edit.model_dump(exclude_none=True)),
    )
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise


async def delete_membership(membership_id: str, db: AsyncSession):
    """Delete a Membership in database"""

    await db.execute(
        delete(models_phonebook.Membership).where(
            models_phonebook.Membership.id == membership_id,
        ),
    )
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise


async def get_memberships_by_user_id(
    user_id: str,
    db: AsyncSession,
) -> Sequence[models_phonebook.Membership]:
    """Return all Memberships with user_id from database"""
    result = await db.execute(
        select(models_phonebook.Membership).where(
            models_phonebook.Membership.user_id == user_id,
        ),
    )
    return result.scalars().all()


async def get_memberships_by_association_id(
    association_id: str,
    db: AsyncSession,
) -> Sequence[models_phonebook.Membership]:
    """Return all Memberships with association_id from database"""

    result = await db.execute(
        select(models_phonebook.Membership).where(
            models_phonebook.Membership.association_id == association_id,
        ),
    )
    return result.scalars().all()


async def get_memberships_by_association_id_and_mandate_year(
    association_id: str,
    mandate_year: int,
    db: AsyncSession,
) -> Sequence[models_phonebook.Membership]:
    """Return all Memberships with association_id and mandate_year from database"""
    result = await db.execute(
        select(models_phonebook.Membership).where(
            models_phonebook.Membership.association_id == association_id,
            models_phonebook.Membership.mandate_year == mandate_year,
        ),
    )
    return result.scalars().all()


async def get_membership_by_association_id_user_id_and_mandate_year(
    association_id: str,
    user_id: str,
    mandate_year: int,
    db: AsyncSession,
) -> models_phonebook.Membership | None:
    """Return all Memberships with association_id user_id and_mandate_year from database"""

    result = await db.execute(
        select(models_phonebook.Membership).where(
            models_phonebook.Membership.association_id == association_id,
            models_phonebook.Membership.user_id == user_id,
            models_phonebook.Membership.mandate_year == mandate_year,
        ),
    )
    return result.scalars().unique().first()


async def get_membership_by_id(
    membership_id: str,
    db: AsyncSession,
) -> models_phonebook.Membership | None:
    """Return the Membership with id from database"""

    result = await db.execute(
        select(models_phonebook.Membership).where(
            models_phonebook.Membership.id == membership_id,
        ),
    )
    return result.scalars().first()
