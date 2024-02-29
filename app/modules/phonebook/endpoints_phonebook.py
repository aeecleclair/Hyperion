import logging
import uuid

from fastapi import Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import models_core, standard_responses
from app.core.groups.groups_type import GroupType
from app.core.module import Module
from app.dependencies import get_db, get_request_id, is_user_a_member
from app.modules.phonebook import cruds_phonebook, models_phonebook, schemas_phonebook
from app.utils.tools import (
    get_file_from_data,
    is_user_member_of_an_allowed_group,
    save_file_as_data,
)

module = Module(
    root="phonebook",
    tag="Phonebook",
    default_allowed_groups_ids=[GroupType.student, GroupType.staff],
)


hyperion_phonebook_logger = logging.getLogger("hyperion.phonebook")


# ---------------------------------------------------------------------------- #
#                                    Get All                                   #
# ---------------------------------------------------------------------------- #
@module.router.get(
    "/phonebook/associations/",
    response_model=list[schemas_phonebook.AssociationComplete] | None,
    status_code=200,
)
async def get_all_associations(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Return all associations from database as a list of AssociationComplete schemas
    """
    return await cruds_phonebook.get_all_associations(db)


@module.router.get(
    "/phonebook/roletags",
    response_model=schemas_phonebook.RoleTagsReturn | None,
    status_code=200,
)
async def get_all_role_tags(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Return all available role tags from database.
    """
    roles = await cruds_phonebook.get_all_role_tags(db)
    roles_schema = schemas_phonebook.RoleTagsReturn(tags=roles)
    return roles_schema


@module.router.get(
    "/phonebook/associations/kinds",
    response_model=schemas_phonebook.KindsReturn | None,
    status_code=200,
)
async def get_all_kinds(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Return all available kinds of from database.
    """
    kinds = await cruds_phonebook.get_all_kinds(db)
    kinds_schema = schemas_phonebook.KindsReturn(kinds=kinds)
    return kinds_schema


# ---------------------------------------------------------------------------- #
#                                  Association                                 #
# ---------------------------------------------------------------------------- #
@module.router.post(
    "/phonebook/associations/",
    response_model=schemas_phonebook.AssociationComplete,
    status_code=201,
)
async def create_association(
    association: schemas_phonebook.AssociationBase,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Create a new association by giving an AssociationBase scheme (contains the association name, description and type)

    **This endpoint is only usable by CAA, BDE**
    """

    if not is_user_member_of_an_allowed_group(
        user=user, allowed_groups=[GroupType.CAA, GroupType.BDE]
    ):
        raise HTTPException(
            status_code=403,
            detail="You are not allowed to create association",
        )

    id = str(uuid.uuid4())
    association_model = models_phonebook.Association(id=id, **association.model_dump())

    try:
        result = await cruds_phonebook.create_association(association_model, db)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))
    return result


@module.router.patch(
    "/phonebook/associations/{association_id}",
    status_code=204,
)
async def update_association(
    association_id: str,
    association_edit: schemas_phonebook.AssociationEdit,
    user: models_core.CoreUser = Depends(is_user_a_member),
    db: AsyncSession = Depends(get_db),
):
    """
    Update an association

    **This endpoint is only usable by CAA, BDE and association's president**
    """
    if not is_user_member_of_an_allowed_group(
        user=user, allowed_groups=[GroupType.CAA, GroupType.BDE]
    ) and not await cruds_phonebook.is_user_president(
        association_id=association_id, user=user, db=db
    ):
        raise HTTPException(
            status_code=403,
            detail=f"You are not allowed to update association {association_id}",
        )

    try:
        await cruds_phonebook.update_association(
            association_id=association_id, association_edit=association_edit, db=db
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))


@module.router.delete(
    "/phonebook/associations/{association_id}",
    status_code=204,
)
async def delete_association(
    association_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Delete an association

    **This endpoint is only usable by CAA and BDE**
    """
    if not is_user_member_of_an_allowed_group(
        user=user, allowed_groups=[GroupType.CAA, GroupType.BDE]
    ):
        raise HTTPException(
            status_code=403,
            detail=f"You are not allowed to delete association {association_id}",
        )
    return await cruds_phonebook.delete_association(
        association_id=association_id, db=db
    )


# ---------------------------------------------------------------------------- #
#                                    Members                                   #
# ---------------------------------------------------------------------------- #


@module.router.get(
    "/phonebook/associations/{association_id}/members/",
    response_model=list[schemas_phonebook.MemberComplete] | None,
    status_code=200,
)
async def get_association_members(
    association_id: str,
    user: models_core.CoreUser = Depends(is_user_a_member),
    db: AsyncSession = Depends(get_db),
):
    """Get the list of memberships of an association."""
    association_memberships = await cruds_phonebook.get_memberships_by_association_id(
        association_id, db
    )

    if association_memberships is None:
        return []

    members_complete = []

    for membership in association_memberships:
        member_id = membership.user_id
        member = await cruds_phonebook.get_member_by_id(member_id=member_id, db=db)
        member_memberships = await cruds_phonebook.get_membership_by_user_id(
            user_id=member_id, db=db
        )
        members_complete.append(
            schemas_phonebook.MemberComplete(
                memberships=member_memberships, **member.__dict__
            )
        )
    return members_complete


@module.router.get(
    "/phonebook/associations/{association_id}/members/{mandate_year}",
    response_model=list[schemas_phonebook.MemberComplete] | None,
    status_code=200,
)
async def get_association_members_by_mandate_year(
    association_id: str,
    mandate_year: int,
    user: models_core.CoreUser = Depends(is_user_a_member),
    db: AsyncSession = Depends(get_db),
):
    """Get the list of memberships of an association."""
    association_memberships = (
        await cruds_phonebook.get_memberships_by_association_id_and_mandate_year(
            association_id=association_id, mandate_year=mandate_year, db=db
        )
    )

    if association_memberships is None:
        return []

    members_complete = []

    for membership in association_memberships:
        member_id = membership.user_id
        member = await cruds_phonebook.get_member_by_id(member_id=member_id, db=db)
        member_memberships = await cruds_phonebook.get_membership_by_user_id(
            user_id=member_id, db=db
        )
        members_complete.append(
            schemas_phonebook.MemberComplete(
                memberships=member_memberships, **member.__dict__
            )
        )
    return members_complete


@module.router.get(
    "/phonebook/member/{user_id}/",
    response_model=schemas_phonebook.MemberComplete,
    status_code=200,
)
async def get_member_details(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    member_memberships = await cruds_phonebook.get_membership_by_user_id(user_id, db)
    if not member_memberships:
        return
    member = await cruds_phonebook.get_member_by_id(user_id, db)
    print(member_memberships)
    return schemas_phonebook.MemberComplete(
        memberships=member_memberships, **member.__dict__
    )


# @module.router.get(
#     "/phonebook/associations/memberships/{membership_id}",
#     response_model=schemas_phonebook.MembershipComplete,
#     status_code=200,
#     tags=[Tags.phonebook]
# )
# async def get_membership_details(
#     membership_id: str,
#     db: AsyncSession = Depends(get_db)
# ) -> schemas_phonebook.MemberBase:
#     return await cruds_phonebook.get_membership_by_


# ---------------------------------------------------------------------------- #
#                                  Membership                                  #
# ---------------------------------------------------------------------------- #
@module.router.post(
    "/phonebook/associations/memberships",
    response_model=schemas_phonebook.MembershipComplete,
    status_code=201,
)
async def create_membership(
    membership: schemas_phonebook.MembershipBase,
    user: models_core.CoreUser = Depends(is_user_a_member),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new membership for a given association, a given user. Tags are used to indicate if
    the members has a main role in the association (president, secretary ...) and
    'role_name' is the display name for this membership

    **This endpoint is only usable by CAA, BDE and association's president**
    """
    if not is_user_member_of_an_allowed_group(
        user=user, allowed_groups=[GroupType.CAA, GroupType.BDE]
    ) and not await cruds_phonebook.is_user_president(
        association_id=membership.association_id, user=user, db=db
    ):
        raise HTTPException(
            status_code=403,
            detail=f"You are not allowed to create a new membership for association {membership.association_id}",
        )

    role_tags = dict(membership).pop("role_tags")
    role_tags = role_tags.split(";")
    association = await cruds_phonebook.get_association_by_id(
        membership.association_id, db
    )
    if association is None:
        raise HTTPException(
            400,
            "Error : No association in the scheme. Can't create the membership. Please add an association id in your membership scheme",
        )

    if (
        await cruds_phonebook.get_memberships_by_association_id_user_id_and_mandate_year(
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

    id = str(uuid.uuid4())

    membership_model = models_phonebook.Membership(id=id, **membership.model_dump())
    # Add the membership
    await cruds_phonebook.create_membership(membership_model, db)
    # Add the roletags to the attributed roletags table
    for role in role_tags:
        await cruds_phonebook.add_new_role(role, id, db)
    return schemas_phonebook.MembershipComplete(**membership_model.__dict__)


@module.router.patch(
    "/phonebook/associations/memberships/{membership_id}",
    status_code=204,
)
async def update_membership(
    membership: schemas_phonebook.MembershipEdit,
    membership_id: str,
    user: models_core.CoreUser = Depends(is_user_a_member),
    db: AsyncSession = Depends(get_db),
):
    """
    Update a membership.

    **This endpoint is only usable by CAA, BDE and association's president**
    """
    membership_db = await cruds_phonebook.get_membership_by_id(
        membership_id=membership_id, db=db
    )
    if not membership_db:
        raise HTTPException(
            status_code=400,
            detail=f"No membership to update for membership_id {membership_id}",
        )

    if not is_user_member_of_an_allowed_group(
        user=user, allowed_groups=[GroupType.CAA, GroupType.BDE]
    ) and not await cruds_phonebook.is_user_president(
        association_id=membership_db.association_id, user=user, db=db
    ):
        raise HTTPException(
            status_code=403,
            detail=f"You are not allowed to update membership for association {membership_db.association_id}",
        )
    role_tags = dict(membership).pop("role_tags")
    if role_tags is not None:
        role_tags = role_tags.split(";")
        db_role_tags = await cruds_phonebook.get_membership_roletags(membership_id, db)
        for role in role_tags:
            if role not in db_role_tags:
                hyperion_phonebook_logger.info("Add role", role)
                await cruds_phonebook.add_new_role(role, membership_id, db)
        for role in db_role_tags:
            if role not in role_tags:
                hyperion_phonebook_logger.info("Delete role", role)
                await cruds_phonebook.delete_role(role, membership_id, db)
    hyperion_phonebook_logger.info("Update membership", membership.model_dump())
    membership_complete = schemas_phonebook.MembershipEdit(**membership.model_dump())
    await cruds_phonebook.update_membership(membership_complete, membership_id, db)


@module.router.delete(
    "/phonebook/associations/memberships/{membership_id}",
    status_code=204,
)
async def delete_membership(
    membership_id: str,
    user: models_core.CoreUser = Depends(is_user_a_member),
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

    if not is_user_member_of_an_allowed_group(
        user=user, allowed_groups=[GroupType.CAA, GroupType.BDE]
    ) and not await cruds_phonebook.is_user_president(
        association_id=membership.association_id, user=user, db=db
    ):
        raise HTTPException(
            status_code=403,
            detail=f"You are not allowed to delete membership for association {membership.association_id}",
        )

    await cruds_phonebook.delete_role_tag(membership_id, db)
    await cruds_phonebook.delete_membership(membership_id, db)


# ---------------------------------------------------------------------------- #
#                                     Logos                                    #
# ---------------------------------------------------------------------------- #
@module.router.post(
    "/phonebook/associations/{association_id}/picture",
    # response_model=standard_responses.Result,
    status_code=201,
)
async def create_association_logo(
    association_id: str,
    image: UploadFile = File(...),
    request_id: str = Depends(get_request_id),
    user: models_core.CoreUser = Depends(is_user_a_member),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload a logo for an association.
    **The user must be a member of the group CAA or BDE to use this endpoint**
    """

    if not is_user_member_of_an_allowed_group(
        user=user, allowed_groups=[GroupType.CAA, GroupType.BDE]
    ) and not await cruds_phonebook.is_user_president(
        association_id=association_id, user=user, db=db
    ):
        raise HTTPException(
            status_code=403,
            detail=f"You are not allowed to update association {association_id}",
        )

    association = await cruds_phonebook.get_association_by_id(association_id, db)
    if association is None:
        raise HTTPException(
            status_code=404,
            detail="The association does not exist.",
        )

    await save_file_as_data(
        image=image,
        directory="associations",
        filename=str(association_id),
        request_id=request_id,
        max_file_size=4 * 1024 * 1024,
        accepted_content_types=["image/jpeg", "image/png", "image/webp"],
    )

    return standard_responses.Result(success=True)


@module.router.get(
    "/phonebook/associations/{association_id}/picture",
    response_class=FileResponse,
    status_code=200,
)
async def read_association_logo(
    association_id: str,
    user: models_core.CoreUser = Depends(is_user_a_member),
) -> FileResponse:
    """
    Get the logo of an association.
    """

    return get_file_from_data(
        directory="associations",
        filename=str(association_id),
        default_asset="assets/images/default_association_picture.png",
    )
