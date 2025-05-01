import logging
import uuid

from fastapi import Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.groups import cruds_groups, models_groups
from app.core.groups.groups_type import AccountType, GroupType
from app.core.users import cruds_users, models_users
from app.dependencies import (
    get_db,
    get_request_id,
    is_user_an_ecl_member,
    is_user_in,
)
from app.modules.phonebook import cruds_phonebook, models_phonebook, schemas_phonebook
from app.modules.phonebook.types_phonebook import RoleTags
from app.types import standard_responses
from app.types.content_type import ContentType
from app.types.module import Module
from app.utils.tools import (
    get_file_from_data,
    is_user_member_of_any_group,
    save_file_as_data,
)

module = Module(
    root="phonebook",
    tag="Phonebook",
    default_allowed_account_types=[AccountType.student, AccountType.staff],
)

hyperion_error_logger = logging.getLogger("hyperion.error")


@module.router.get(
    "/phonebook/associations/",
    response_model=list[schemas_phonebook.AssociationComplete],
    status_code=200,
)
async def get_all_associations(
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_an_ecl_member),
):
    """
    Return all associations from database as a list of AssociationComplete schemas
    """
    associations = await cruds_phonebook.get_all_associations(db)
    return [
        schemas_phonebook.AssociationComplete(
            id=association.id,
            name=association.name,
            kind=association.kind,
            mandate_year=association.mandate_year,
            description=association.description,
            associated_groups=[group.id for group in association.associated_groups],
            deactivated=association.deactivated,
        )
        for association in associations
    ]


@module.router.get(
    "/phonebook/roletags",
    response_model=schemas_phonebook.RoleTagsReturn,
    status_code=200,
)
async def get_all_role_tags(
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_an_ecl_member),
):
    """
    Return all available role tags from RoleTags enum.
    """
    roles = await cruds_phonebook.get_all_role_tags()
    return schemas_phonebook.RoleTagsReturn(tags=roles)


@module.router.get(
    "/phonebook/associations/kinds",
    response_model=schemas_phonebook.KindsReturn,
    status_code=200,
)
async def get_all_kinds(
    user: models_users.CoreUser = Depends(is_user_an_ecl_member),
):
    """
    Return all available kinds of from Kinds enum.
    """
    kinds = await cruds_phonebook.get_all_kinds()
    return schemas_phonebook.KindsReturn(kinds=kinds)


@module.router.post(
    "/phonebook/associations/",
    response_model=schemas_phonebook.AssociationComplete,
    status_code=201,
)
async def create_association(
    association: schemas_phonebook.AssociationBase,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_an_ecl_member),
):
    """
    Create a new Association by giving an AssociationBase scheme

    **This endpoint is only usable by CAA, BDE**
    """

    if not is_user_member_of_any_group(
        user=user,
        allowed_groups=[GroupType.CAA, GroupType.BDE],
    ):
        raise HTTPException(
            status_code=403,
            detail="You are not allowed to create association",
        )

    association_id = str(uuid.uuid4())
    association_model = models_phonebook.Association(
        id=association_id,
        name=association.name,
        description=association.description,
        kind=association.kind,
        mandate_year=association.mandate_year,
        deactivated=association.deactivated,
    )

    await cruds_phonebook.create_association(association_model, db)

    await cruds_phonebook.update_association_groups(
        association_id=association_id,
        new_associated_group_ids=association.associated_groups,
        db=db,
    )

    return schemas_phonebook.AssociationComplete(
        id=association_id,
        **association.model_dump(),
    )


@module.router.patch(
    "/phonebook/associations/{association_id}",
    status_code=204,
)
async def update_association(
    association_id: str,
    association_edit: schemas_phonebook.AssociationEdit,
    user: models_users.CoreUser = Depends(is_user_an_ecl_member),
    db: AsyncSession = Depends(get_db),
):
    """
    Update an Association

    **This endpoint is only usable by CAA, BDE and association's president**
    """
    if not (
        is_user_member_of_any_group(
            user=user,
            allowed_groups=[GroupType.CAA, GroupType.BDE],
        )
        or await cruds_phonebook.is_user_president(
            association_id=association_id,
            user=user,
            db=db,
        )
    ):
        raise HTTPException(
            status_code=403,
            detail=f"You are not allowed to update association {association_id}",
        )

    try:
        await cruds_phonebook.update_association(
            association_id=association_id,
            association_edit=association_edit,
            db=db,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))


@module.router.patch(
    "/phonebook/associations/{association_id}/groups",
    status_code=204,
)
async def update_association_groups(
    association_id: str,
    association_groups_edit: schemas_phonebook.AssociationGroupsEdit,
    user: models_users.CoreUser = Depends(is_user_in(GroupType.admin)),
    db: AsyncSession = Depends(get_db),
):
    """
    Update the groups associated with an Association

    **This endpoint is only usable by Admins (not BDE and CAA)**
    """
    await cruds_phonebook.update_association_groups(
        association_id=association_id,
        new_associated_group_ids=association_groups_edit.associated_groups,
        db=db,
    )


@module.router.patch(
    "/phonebook/associations/{association_id}/deactivate",
    status_code=204,
)
async def deactivate_association(
    association_id: str,
    user: models_users.CoreUser = Depends(is_user_an_ecl_member),
    db: AsyncSession = Depends(get_db),
):
    """
    Deactivate an Association

    **This endpoint is only usable by CAA and BDE**
    """
    if not is_user_member_of_any_group(
        user=user,
        allowed_groups=[GroupType.CAA, GroupType.BDE],
    ):
        raise HTTPException(
            status_code=403,
            detail=f"You are not allowed to delete association {association_id}",
        )
    await cruds_phonebook.deactivate_association(association_id, db)


@module.router.delete(
    "/phonebook/associations/{association_id}",
    status_code=204,
)
async def delete_association(
    association_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_an_ecl_member),
):
    """
    Delete an Association

    [!] Memberships linked to association_id will be deleted too

    **This endpoint is only usable by CAA and BDE**
    """

    if not is_user_member_of_any_group(
        user=user,
        allowed_groups=[GroupType.CAA, GroupType.BDE],
    ):
        raise HTTPException(
            status_code=403,
            detail=f"You are not allowed to delete association {association_id}",
        )
    association = await cruds_phonebook.get_association_by_id(association_id, db)
    if association is None:
        raise HTTPException(404, "Association does not exist.")
    if not association.deactivated:
        raise HTTPException(
            400,
            "Only deactivated associations can be deleted.",
        )
    return await cruds_phonebook.delete_association(
        association_id=association_id,
        db=db,
    )


@module.router.get(
    "/phonebook/associations/{association_id}/members/",
    response_model=list[schemas_phonebook.MemberComplete],
    status_code=200,
)
async def get_association_members(
    association_id: str,
    user: models_users.CoreUser = Depends(is_user_an_ecl_member),
    db: AsyncSession = Depends(get_db),
):
    """Return the list of MemberComplete of an Association."""

    association_memberships = await cruds_phonebook.get_memberships_by_association_id(
        association_id,
        db,
    )

    members_complete = []

    for membership in association_memberships:
        member_id = membership.user_id
        member = await cruds_users.get_user_by_id(user_id=member_id, db=db)
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


@module.router.get(
    "/phonebook/associations/{association_id}/members/{mandate_year}",
    response_model=list[schemas_phonebook.MemberComplete],
    status_code=200,
)
async def get_association_members_by_mandate_year(
    association_id: str,
    mandate_year: int,
    user: models_users.CoreUser = Depends(is_user_an_ecl_member),
    db: AsyncSession = Depends(get_db),
):
    """Return the list of MemberComplete of an Association with given mandate_year."""

    association_memberships = (
        await cruds_phonebook.get_memberships_by_association_id_and_mandate_year(
            association_id=association_id,
            mandate_year=mandate_year,
            db=db,
        )
    )

    members_complete = []

    for membership in association_memberships:
        member_id = membership.user_id
        member = await cruds_users.get_user_by_id(user_id=member_id, db=db)
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


@module.router.get(
    "/phonebook/member/{user_id}",
    response_model=schemas_phonebook.MemberComplete,
    status_code=200,
)
async def get_member_details(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_an_ecl_member),
):
    """Return MemberComplete for given user_id."""

    member_memberships = await cruds_phonebook.get_memberships_by_user_id(user_id, db)

    member = await cruds_users.get_user_by_id(user_id=user_id, db=db)

    if member is None:
        raise HTTPException(404, "Member does not exist.")

    return schemas_phonebook.MemberComplete(
        memberships=member_memberships,
        **member.__dict__,
    )


@module.router.post(
    "/phonebook/associations/memberships",
    response_model=schemas_phonebook.MembershipComplete,
    status_code=201,
)
async def create_membership(
    membership: schemas_phonebook.MembershipBase,
    user: models_users.CoreUser = Depends(is_user_an_ecl_member),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new Membership.
    'role_tags' are used to indicate if the members has a main role in the association (president, secretary ...) and 'role_name' is the display name for this membership

    **This endpoint is only usable by CAA, BDE and association's president**
    """

    user_added = await cruds_users.get_user_by_id(db, membership.user_id)
    if user_added is None:
        raise HTTPException(
            400,
            "Error : User does not exist",
        )

    if not (
        is_user_member_of_any_group(
            user=user,
            allowed_groups=[GroupType.CAA, GroupType.BDE],
        )
        or await cruds_phonebook.is_user_president(
            association_id=membership.association_id,
            user=user,
            db=db,
        )
    ):
        raise HTTPException(
            status_code=403,
            detail=f"You are not allowed to create a new membership for association {membership.association_id}",
        )

    if membership.role_tags is not None:
        if RoleTags.president.value in membership.role_tags.split(
            ";",
        ) and not is_user_member_of_any_group(
            user=user,
            allowed_groups=[GroupType.CAA, GroupType.BDE],
        ):
            raise HTTPException(
                status_code=403,
                detail="You are not allowed to update a membership with the role of president",
            )

    association = await cruds_phonebook.get_association_by_id(
        membership.association_id,
        db,
    )
    if association is None:
        raise HTTPException(
            400,
            "Error : Association does not exist",
        )
    if association.deactivated:
        raise HTTPException(
            400,
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
        raise HTTPException(
            400,
            "Error : Membership already exists, try modifying the existing one",
        )

    membershipId = str(uuid.uuid4())
    membership_model = models_phonebook.Membership(
        id=membershipId,
        **membership.model_dump(),
    )

    await cruds_phonebook.create_membership(membership_model, db)

    user_groups_id = [group.id for group in user_added.groups]
    for associated_group in association.associated_groups:
        if associated_group.id not in user_groups_id:
            await cruds_groups.create_membership(
                models_groups.CoreMembership(
                    user_id=membership.user_id,
                    group_id=associated_group.id,
                    description=None,
                ),
                db,
            )
    return schemas_phonebook.MembershipComplete(**membership_model.__dict__)


@module.router.patch(
    "/phonebook/associations/memberships/{membership_id}",
    status_code=204,
)
async def update_membership(
    updated_membership: schemas_phonebook.MembershipEdit,
    membership_id: str,
    user: models_users.CoreUser = Depends(is_user_an_ecl_member),
    db: AsyncSession = Depends(get_db),
):
    """
    Update a Membership.

    **This endpoint is only usable by CAA, BDE and association's president**
    """

    old_membership = await cruds_phonebook.get_membership_by_id(
        membership_id=membership_id,
        db=db,
    )
    if not old_membership:
        raise HTTPException(
            status_code=400,
            detail=f"No membership to update for membership_id {membership_id}",
        )

    if not (
        is_user_member_of_any_group(
            user=user,
            allowed_groups=[GroupType.CAA, GroupType.BDE],
        )
        or await cruds_phonebook.is_user_president(
            association_id=old_membership.association_id,
            user=user,
            db=db,
        )
    ):
        raise HTTPException(
            status_code=403,
            detail=f"You are not allowed to update membership for association {old_membership.association_id}",
        )

    if updated_membership.role_tags is not None:
        if RoleTags.president.value in updated_membership.role_tags.split(
            ";",
        ) and not is_user_member_of_any_group(
            user=user,
            allowed_groups=[GroupType.CAA, GroupType.BDE],
        ):
            raise HTTPException(
                status_code=403,
                detail="Only CAA and BDE can update a membership with the role of president",
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


@module.router.delete(
    "/phonebook/associations/memberships/{membership_id}",
    status_code=204,
)
async def delete_membership(
    membership_id: str,
    user: models_users.CoreUser = Depends(is_user_an_ecl_member),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a membership.

    **This endpoint is only usable by CAA, BDE and association's president**
    """

    membership = await cruds_phonebook.get_membership_by_id(membership_id, db)
    if not membership:
        raise HTTPException(
            status_code=400,
            detail=f"No membership to delete for membership_id {membership_id}",
        )

    if not (
        is_user_member_of_any_group(
            user=user,
            allowed_groups=[GroupType.CAA, GroupType.BDE],
        )
        or await cruds_phonebook.is_user_president(
            association_id=membership.association_id,
            user=user,
            db=db,
        )
    ):
        raise HTTPException(
            status_code=403,
            detail=f"You are not allowed to delete membership for association {membership.association_id}",
        )

    await cruds_phonebook.update_order_of_memberships(
        db,
        membership.association_id,
        membership.mandate_year,
        membership.member_order,
    )

    await cruds_phonebook.delete_membership(membership_id, db)


@module.router.post(
    "/phonebook/associations/{association_id}/picture",
    response_model=standard_responses.Result,
    status_code=201,
)
async def create_association_logo(
    association_id: str,
    image: UploadFile = File(),
    request_id: str = Depends(get_request_id),
    user: models_users.CoreUser = Depends(is_user_an_ecl_member),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload a logo for an Association.
    **The user must be a member of the group CAA or BDE to use this endpoint**
    """

    if not is_user_member_of_any_group(
        user=user,
        allowed_groups=[GroupType.CAA, GroupType.BDE],
    ) and not await cruds_phonebook.is_user_president(
        association_id=association_id,
        user=user,
        db=db,
    ):
        raise HTTPException(
            status_code=403,
            detail=f"You are not allowed to update association {association_id}",
        )

    association = await cruds_phonebook.get_association_by_id(association_id, db)
    if association is None:
        raise HTTPException(
            status_code=404,
            detail="The Association does not exist.",
        )

    await save_file_as_data(
        upload_file=image,
        directory="associations",
        filename=association_id,
        request_id=request_id,
        max_file_size=4 * 1024 * 1024,
        accepted_content_types=[
            ContentType.jpg,
            ContentType.png,
            ContentType.webp,
        ],
    )
    return standard_responses.Result(success=True)


@module.router.get(
    "/phonebook/associations/{association_id}/picture",
    response_class=FileResponse,
    status_code=200,
)
async def read_association_logo(
    association_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_an_ecl_member),
) -> FileResponse:
    """
    Get the logo of an Association.
    """
    association = await cruds_phonebook.get_association_by_id(association_id, db)

    if association is None:
        raise HTTPException(404, "The Association does not exist.")

    return get_file_from_data(
        directory="associations",
        filename=association_id,
        default_asset="assets/images/default_association_picture.png",
    )
