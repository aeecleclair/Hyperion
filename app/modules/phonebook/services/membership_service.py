import uuid
from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.groups import cruds_groups, models_groups
from app.core.users import cruds_users, models_users, schemas_users
from app.modules.phonebook import cruds_phonebook, schemas_phonebook
from app.modules.phonebook.others import exceptions_phonebook
from app.modules.phonebook.others.shared import (
    association_if_exists,
    has_association_groupement_manager_rights,
    validate_rights_or_is_president,
)
from app.modules.phonebook.others.types_phonebook import RoleTags


async def get_all_role_tags() -> schemas_phonebook.RoleTagsReturn:
    roles = [tag.value for tag in RoleTags]
    return schemas_phonebook.RoleTagsReturn(tags=roles)


async def memberships_to_members(
    association_memberships: Sequence[schemas_phonebook.MembershipComplete],
    db: AsyncSession,
) -> list[schemas_phonebook.MemberComplete]:
    members_complete = []
    for membership in association_memberships:
        member_id = membership.user_id
        member = await cruds_users.get_user_by_id_schema(user_id=member_id, db=db)
        member_memberships = await cruds_phonebook.get_memberships_by_user_id(
            user_id=member_id,
            db=db,
        )
        members_complete.append(
            schemas_phonebook.MemberComplete(
                memberships=member_memberships,
                **member.__dict__,
            ),
        )
    return members_complete


async def user_if_exists(
    db: AsyncSession,
    user_id: str,
) -> schemas_users.CoreUser:
    user = await cruds_users.get_user_by_id_schema(db, user_id)
    if user is None:
        raise exceptions_phonebook.BadRequestException(  # noqa: TRY003
            "Error : User does not exist",
        )
    return user


async def membership_if_exists(
    membership_id: str,
    db: AsyncSession,
    detail: str,
) -> schemas_phonebook.MembershipComplete:
    membership = await cruds_phonebook.get_membership_by_id(membership_id, db)
    if not membership:
        raise exceptions_phonebook.BadRequestException(detail)
    return membership


async def validate_rights_or_no_president_update(
    role_tags: str | None,
    groupement_id: uuid.UUID,
    user: models_users.CoreUser,
    db: AsyncSession,
    detail: str,
):
    if role_tags is not None:
        if RoleTags.president.value in role_tags.split(
            ";",
        ) and not await has_association_groupement_manager_rights(
            db=db,
            user=user,
            groupement_id=groupement_id,
        ):
            raise exceptions_phonebook.ForbiddenException(detail)


async def get_association_members(
    association_id: str,
    db: AsyncSession,
) -> list[schemas_phonebook.MemberComplete]:
    association_memberships = await cruds_phonebook.get_memberships_by_association_id(
        association_id,
        db,
    )
    return await memberships_to_members(association_memberships, db)


async def get_association_members_by_mandate_year(
    association_id: str,
    mandate_year: int,
    db: AsyncSession,
) -> list[schemas_phonebook.MemberComplete]:
    association_memberships = (
        await cruds_phonebook.get_memberships_by_association_id_and_mandate_year(
            association_id=association_id,
            mandate_year=mandate_year,
            db=db,
        )
    )
    return await memberships_to_members(association_memberships, db)


async def get_member_details(
    user_id: str,
    db: AsyncSession,
) -> schemas_phonebook.MemberComplete:
    member_memberships = await cruds_phonebook.get_memberships_by_user_id(user_id, db)
    member = await user_if_exists(db, user_id)

    return schemas_phonebook.MemberComplete(
        memberships=member_memberships,
        **member.__dict__,
    )


async def create_membership(
    membership: schemas_phonebook.MembershipBase,
    user: models_users.CoreUser,
    db: AsyncSession,
) -> schemas_phonebook.MembershipComplete:
    user_added = await user_if_exists(db, membership.user_id)
    association = await association_if_exists(membership.association_id, db)
    await validate_rights_or_is_president(
        membership.association_id,
        association.mandate_year,
        association.groupement_id,
        user,
        db,
        f"You are not allowed to create a new membership for association {membership.association_id}",
    )
    await validate_rights_or_no_president_update(
        membership.role_tags,
        association.groupement_id,
        user,
        db,
        "You are not allowed to update a membership with the role of president",
    )

    if association.deactivated:
        raise exceptions_phonebook.BadRequestException(  # noqa: TRY003
            "Error : Association is deactivated",
        )

    if (
        await cruds_phonebook.get_membership_by_association_id_user_id_and_mandate_year(
            association_id=membership.association_id,
            user_id=membership.user_id,
            mandate_year=membership.mandate_year,
            db=db,
        )
        is not None
    ):
        raise exceptions_phonebook.BadRequestException(  # noqa: TRY003
            "Error : Membership already exists, try modifying the existing one",
        )

    membershipId = str(uuid.uuid4())
    membership_model = schemas_phonebook.MembershipComplete(
        id=membershipId,
        user_id=membership.user_id,
        association_id=membership.association_id,
        mandate_year=membership.mandate_year,
        role_name=membership.role_name,
        role_tags=membership.role_tags,
        member_order=membership.member_order,
    )

    await cruds_phonebook.create_membership(membership_model, db)

    user_groups_id = [group.id for group in user_added.groups]
    for associated_group_id in association.associated_groups:
        if associated_group_id not in user_groups_id:
            await cruds_groups.create_membership(
                models_groups.CoreMembership(
                    user_id=membership.user_id,
                    group_id=associated_group_id,
                    description=None,
                ),
                db,
            )
    return schemas_phonebook.MembershipComplete(**membership_model.__dict__)


async def update_membership(
    updated_membership: schemas_phonebook.MembershipEdit,
    membership_id: str,
    user: models_users.CoreUser,
    db: AsyncSession,
) -> None:
    old_membership = await membership_if_exists(
        membership_id,
        db,
        f"No membership to update for membership_id {membership_id}",
    )

    association = await association_if_exists(old_membership.association_id, db)

    await validate_rights_or_is_president(
        old_membership.association_id,
        association.mandate_year,
        association.groupement_id,
        user,
        db,
        f"You are not allowed to update membership for association {old_membership.association_id}",
    )

    await validate_rights_or_no_president_update(
        updated_membership.role_tags,
        association.groupement_id,
        user,
        db,
        "Only PhonebookAdmin and Groupement manager can update a membership with the role of president",
    )

    if updated_membership.member_order is not None:
        await cruds_phonebook.update_order_of_memberships(
            db,
            old_membership.association_id,
            old_membership.mandate_year,
            old_membership.member_order,
            updated_membership.member_order,
        )

    # We update the membership after updating the member_order to avoid conflicts
    await cruds_phonebook.update_membership(updated_membership, membership_id, db)


async def delete_membership(
    membership_id: str,
    user: models_users.CoreUser,
    db: AsyncSession,
) -> None:
    membership = await membership_if_exists(
        membership_id,
        db,
        f"No membership to delete for membership_id {membership_id}",
    )
    association = await association_if_exists(membership.association_id, db)

    await validate_rights_or_is_president(
        membership.association_id,
        association.mandate_year,
        association.groupement_id,
        user,
        db,
        f"You are not allowed to delete membership for association {membership.association_id}",
    )

    await cruds_phonebook.update_order_of_memberships(
        db,
        membership.association_id,
        membership.mandate_year,
        membership.member_order,
    )

    await cruds_phonebook.delete_membership(membership_id, db)
