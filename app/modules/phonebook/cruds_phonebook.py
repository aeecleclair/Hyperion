from collections.abc import Sequence

from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.users import models_users
from app.modules.phonebook import models_phonebook, schemas_phonebook, types_phonebook


# ---------------------------------------------------------------------------- #
#                               President test                                 #
# ---------------------------------------------------------------------------- #
async def is_user_president(
    association_id: str,
    user: models_users.CoreUser,
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
    await db.flush()
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
    await db.flush()


async def update_association_groups(
    association_id: str,
    new_associated_group_ids: list[str],
    db: AsyncSession,
):
    """Update the associated_groups of an Association in database"""

    await db.execute(
        delete(models_phonebook.AssociationAssociatedGroups).where(
            models_phonebook.AssociationAssociatedGroups.association_id
            == association_id,
        ),
    )
    for group_id in new_associated_group_ids:
        db.add(
            models_phonebook.AssociationAssociatedGroups(
                association_id=association_id,
                group_id=group_id,
            ),
        )
    await db.flush()


async def deactivate_association(association_id: str, db: AsyncSession):
    """Deactivate an Association in database"""

    await db.execute(
        update(models_phonebook.Association)
        .where(models_phonebook.Association.id == association_id)
        .values(deactivated=True),
    )
    await db.flush()


async def delete_association(association_id: str, db: AsyncSession):
    """Delete an Association from database"""

    await db.execute(  # Memberships from the Association must be deleted first
        delete(models_phonebook.Membership).where(
            models_phonebook.Membership.association_id == association_id,
        ),
    )
    await db.execute(  # AssociatedGroups from the Association must be deleted first
        delete(models_phonebook.AssociationAssociatedGroups).where(
            models_phonebook.AssociationAssociatedGroups.association_id
            == association_id,
        ),
    )
    await db.execute(
        delete(models_phonebook.Association).where(
            models_phonebook.Association.id == association_id,
        ),
    )
    await db.flush()


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


async def get_associated_groups_by_association_id(
    association_id: str,
    db: AsyncSession,
) -> Sequence[models_phonebook.AssociationAssociatedGroups]:
    """Return all AssociatedGroups with association_id from database"""

    result = await db.execute(
        select(models_phonebook.AssociationAssociatedGroups).where(
            models_phonebook.AssociationAssociatedGroups.association_id
            == association_id,
        ),
    )
    return result.scalars().all()


# ---------------------------------------------------------------------------- #
#                                  Membership                                  #
# ---------------------------------------------------------------------------- #
async def create_membership(membership: models_phonebook.Membership, db: AsyncSession):
    """Create a Membership in database"""
    db.add(membership)
    await db.flush()


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
    await db.flush()


async def update_order_of_memberships(
    db: AsyncSession,
    association_id: str,
    mandate_year: int,
    old_order: int,
    new_order: int | None = None,
):
    """
    Shift the member_order of Memberships between `old_order` and `new_order`. This crud should be used to keep orders coherent when inserting, moving or removing a membership.
    The cruds won't update the membership that was at the `old_order`, you must call an other crud to update, or remove it to prevent member_order collisions. This cruds should be called first."""

    if new_order is None:
        await db.execute(
            update(models_phonebook.Membership)
            .where(
                models_phonebook.Membership.association_id == association_id,
                models_phonebook.Membership.mandate_year == mandate_year,
                models_phonebook.Membership.member_order > old_order,
            )
            .values(member_order=models_phonebook.Membership.member_order - 1),
        )

    elif old_order > new_order:
        await db.execute(
            update(models_phonebook.Membership)
            .where(
                models_phonebook.Membership.association_id == association_id,
                models_phonebook.Membership.mandate_year == mandate_year,
                models_phonebook.Membership.member_order >= new_order,
                models_phonebook.Membership.member_order < old_order,
            )
            .values(member_order=models_phonebook.Membership.member_order + 1),
        )
    else:
        await db.execute(
            update(models_phonebook.Membership)
            .where(
                models_phonebook.Membership.association_id == association_id,
                models_phonebook.Membership.mandate_year == mandate_year,
                models_phonebook.Membership.member_order > old_order,
                models_phonebook.Membership.member_order <= new_order,
            )
            .values(member_order=models_phonebook.Membership.member_order - 1),
        )
    await db.flush()


async def delete_membership(membership_id: str, db: AsyncSession):
    """Delete a Membership in database"""

    await db.execute(
        delete(models_phonebook.Membership).where(
            models_phonebook.Membership.id == membership_id,
        ),
    )
    await db.flush()


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
        select(models_phonebook.Membership)
        .where(
            models_phonebook.Membership.association_id == association_id,
        )
        .order_by(models_phonebook.Membership.member_order),
    )
    return result.scalars().all()


async def get_memberships_by_association_id_and_mandate_year(
    association_id: str,
    mandate_year: int,
    db: AsyncSession,
) -> Sequence[models_phonebook.Membership]:
    """Return all Memberships with association_id and mandate_year from database"""
    result = await db.execute(
        select(models_phonebook.Membership)
        .where(
            models_phonebook.Membership.association_id == association_id,
            models_phonebook.Membership.mandate_year == mandate_year,
        )
        .order_by(models_phonebook.Membership.member_order),
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
