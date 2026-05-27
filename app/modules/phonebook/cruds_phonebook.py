from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.users import models_users
from app.modules.phonebook import models_phonebook, schemas_phonebook, types_phonebook


# ---------------------------------------------------------------------------- #
#                               President test                                 #
# ---------------------------------------------------------------------------- #
async def is_user_president(
    association_id: str,
    mandate_year: int,
    user: models_users.CoreUser,
    db: AsyncSession,
) -> bool:
    membership = await get_membership_by_association_id_user_id_and_mandate_year(
        association_id=association_id,
        user_id=user.id,
        mandate_year=mandate_year,
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
) -> Sequence[schemas_phonebook.AssociationComplete]:
    """Return all Associations from database"""

    result = await db.execute(
        select(models_phonebook.Association).options(
            selectinload(models_phonebook.Association.associated_groups),
        ),
    )
    return [
        schemas_phonebook.AssociationComplete(
            id=association.id,
            name=association.name,
            description=association.description,
            groupement_id=association.groupement_id,
            mandate_year=association.mandate_year,
            deactivated=association.deactivated,
            associated_groups=[group.id for group in association.associated_groups],
        )
        for association in result.scalars().all()
    ]


async def get_all_role_tags() -> list[str]:
    """Return all RoleTags from Enum"""

    return [tag.value for tag in types_phonebook.RoleTags]


async def get_all_groupements(
    db: AsyncSession,
) -> Sequence[schemas_phonebook.AssociationGroupement]:
    """Return all Groupements from database"""

    result = await db.execute(
        select(models_phonebook.AssociationGroupement).order_by(
            models_phonebook.AssociationGroupement.name,
        ),
    )
    return [
        schemas_phonebook.AssociationGroupement(
            id=groupement.id,
            name=groupement.name,
            manager_group_id=groupement.manager_group_id,
        )
        for groupement in result.scalars().all()
    ]


# ---------------------------------------------------------------------------- #
#                                  Groupement                                  #
# ---------------------------------------------------------------------------- #


async def get_groupement_by_id(
    groupement_id: UUID,
    db: AsyncSession,
) -> schemas_phonebook.AssociationGroupement | None:
    """Return Groupement with id from database"""

    result = (
        (
            await db.execute(
                select(models_phonebook.AssociationGroupement).where(
                    models_phonebook.AssociationGroupement.id == groupement_id,
                ),
            )
        )
        .scalars()
        .first()
    )
    return (
        schemas_phonebook.AssociationGroupement(
            id=result.id,
            name=result.name,
            manager_group_id=result.manager_group_id,
        )
        if result
        else None
    )


async def get_groupement_by_name(
    groupement_name: str,
    db: AsyncSession,
) -> schemas_phonebook.AssociationGroupement | None:
    """Return Groupement with name from database"""

    result = (
        (
            await db.execute(
                select(models_phonebook.AssociationGroupement).where(
                    models_phonebook.AssociationGroupement.name == groupement_name,
                ),
            )
        )
        .scalars()
        .first()
    )
    return (
        schemas_phonebook.AssociationGroupement(
            id=result.id,
            name=result.name,
            manager_group_id=result.manager_group_id,
        )
        if result
        else None
    )


async def create_groupement(
    groupement: schemas_phonebook.AssociationGroupement,
    db: AsyncSession,
) -> None:
    """Create a new Groupement in database and return it"""

    db.add(
        models_phonebook.AssociationGroupement(
            id=groupement.id,
            name=groupement.name,
            manager_group_id=groupement.manager_group_id,
        ),
    )
    await db.flush()


async def update_groupement(
    groupement_id: UUID,
    groupement_edit: schemas_phonebook.AssociationGroupementBase,
    db: AsyncSession,
) -> None:
    """Update a Groupement in database"""

    await db.execute(
        update(models_phonebook.AssociationGroupement)
        .where(models_phonebook.AssociationGroupement.id == groupement_id)
        .values(**groupement_edit.model_dump(exclude_none=True)),
    )
    await db.flush()


async def delete_groupement(
    groupement_id: UUID,
    db: AsyncSession,
) -> None:
    """Delete a Groupement from database"""

    await db.execute(
        delete(models_phonebook.AssociationGroupement).where(
            models_phonebook.AssociationGroupement.id == groupement_id,
        ),
    )
    await db.flush()


# ---------------------------------------------------------------------------- #
#                                  Association                                 #
# ---------------------------------------------------------------------------- #
async def create_association(
    association: schemas_phonebook.AssociationComplete,
    db: AsyncSession,
) -> None:
    """Create a new Association in database and return it"""

    db.add(
        models_phonebook.Association(
            id=association.id,
            name=association.name,
            description=association.description,
            groupement_id=association.groupement_id,
            mandate_year=association.mandate_year,
            deactivated=association.deactivated,
        ),
    )
    await db.flush()


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
) -> schemas_phonebook.AssociationComplete | None:
    """Return Association with id from database"""

    result = (
        (
            await db.execute(
                select(models_phonebook.Association)
                .where(
                    models_phonebook.Association.id == association_id,
                )
                .options(selectinload(models_phonebook.Association.associated_groups)),
            )
        )
        .scalars()
        .first()
    )
    return (
        schemas_phonebook.AssociationComplete(
            id=result.id,
            name=result.name,
            description=result.description,
            groupement_id=result.groupement_id,
            mandate_year=result.mandate_year,
            deactivated=result.deactivated,
            associated_groups=[group.id for group in result.associated_groups],
        )
        if result
        else None
    )


async def get_associations_by_groupement_id(
    groupement_id: UUID,
    db: AsyncSession,
) -> Sequence[schemas_phonebook.AssociationComplete]:
    """Return all Associations with groupement_id from database"""

    result = (
        (
            await db.execute(
                select(models_phonebook.Association).where(
                    models_phonebook.Association.groupement_id == groupement_id,
                ),
            )
        )
        .scalars()
        .all()
    )
    return [
        schemas_phonebook.AssociationComplete(
            id=association.id,
            name=association.name,
            description=association.description,
            groupement_id=association.groupement_id,
            mandate_year=association.mandate_year,
            deactivated=association.deactivated,
            associated_groups=[],
        )
        for association in result
    ]


# ---------------------------------------------------------------------------- #
#                                  Membership                                  #
# ---------------------------------------------------------------------------- #
async def create_membership(
    membership: schemas_phonebook.MembershipComplete,
    db: AsyncSession,
):
    """Create a Membership in database"""
    db.add(
        models_phonebook.Membership(
            id=membership.id,
            user_id=membership.user_id,
            association_id=membership.association_id,
            mandate_year=membership.mandate_year,
            role_name=membership.role_name,
            role_tags=membership.role_tags or "",
            member_order=membership.member_order,
        ),
    )
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
) -> list[schemas_phonebook.MembershipComplete]:
    """Return all Memberships with user_id from database"""
    result = (
        (
            await db.execute(
                select(models_phonebook.Membership).where(
                    models_phonebook.Membership.user_id == user_id,
                ),
            )
        )
        .scalars()
        .all()
    )
    return [
        schemas_phonebook.MembershipComplete(
            id=membership.id,
            user_id=membership.user_id,
            association_id=membership.association_id,
            mandate_year=membership.mandate_year,
            role_name=membership.role_name,
            role_tags=membership.role_tags,
            member_order=membership.member_order,
        )
        for membership in result
    ]


async def get_memberships_by_association_id(
    association_id: str,
    db: AsyncSession,
) -> Sequence[schemas_phonebook.MembershipComplete]:
    """Return all Memberships with association_id from database"""

    result = (
        (
            await db.execute(
                select(models_phonebook.Membership)
                .where(
                    models_phonebook.Membership.association_id == association_id,
                )
                .order_by(models_phonebook.Membership.member_order),
            )
        )
        .scalars()
        .all()
    )
    return [
        schemas_phonebook.MembershipComplete(
            id=membership.id,
            user_id=membership.user_id,
            association_id=membership.association_id,
            mandate_year=membership.mandate_year,
            role_name=membership.role_name,
            role_tags=membership.role_tags,
            member_order=membership.member_order,
        )
        for membership in result
    ]


async def get_memberships_by_association_id_and_mandate_year(
    association_id: str,
    mandate_year: int,
    db: AsyncSession,
) -> Sequence[schemas_phonebook.MembershipComplete]:
    """Return all Memberships with association_id and mandate_year from database"""
    result = (
        (
            await db.execute(
                select(models_phonebook.Membership)
                .where(
                    models_phonebook.Membership.association_id == association_id,
                    models_phonebook.Membership.mandate_year == mandate_year,
                )
                .order_by(models_phonebook.Membership.member_order),
            )
        )
        .scalars()
        .all()
    )
    return [
        schemas_phonebook.MembershipComplete(
            id=membership.id,
            user_id=membership.user_id,
            association_id=membership.association_id,
            mandate_year=membership.mandate_year,
            role_name=membership.role_name,
            role_tags=membership.role_tags,
            member_order=membership.member_order,
        )
        for membership in result
    ]


async def get_membership_by_association_id_user_id_and_mandate_year(
    association_id: str,
    user_id: str,
    mandate_year: int,
    db: AsyncSession,
) -> schemas_phonebook.MembershipComplete | None:
    """Return all Memberships with association_id user_id and_mandate_year from database"""

    result = (
        (
            await db.execute(
                select(models_phonebook.Membership).where(
                    models_phonebook.Membership.association_id == association_id,
                    models_phonebook.Membership.user_id == user_id,
                    models_phonebook.Membership.mandate_year == mandate_year,
                ),
            )
        )
        .scalars()
        .first()
    )
    return (
        schemas_phonebook.MembershipComplete(
            id=result.id,
            user_id=result.user_id,
            association_id=result.association_id,
            mandate_year=result.mandate_year,
            role_name=result.role_name,
            role_tags=result.role_tags,
            member_order=result.member_order,
        )
        if result
        else None
    )


async def get_membership_by_id(
    membership_id: str,
    db: AsyncSession,
) -> schemas_phonebook.MembershipComplete | None:
    """Return Membership with id from database"""

    result = (
        (
            await db.execute(
                select(models_phonebook.Membership).where(
                    models_phonebook.Membership.id == membership_id,
                ),
            )
        )
        .scalars()
        .first()
    )
    return (
        schemas_phonebook.MembershipComplete(
            id=result.id,
            user_id=result.user_id,
            association_id=result.association_id,
            mandate_year=result.mandate_year,
            role_name=result.role_name,
            role_tags=result.role_tags,
            member_order=result.member_order,
        )
        if result
        else None
    )
