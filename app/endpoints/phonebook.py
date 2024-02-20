import datetime
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.cruds import cruds_phonebook
from app.dependencies import get_db, get_request_id, is_user_a_member_of
from app.models import models_core, models_phonebook
from app.schemas import schemas_phonebook
from app.utils.tools import get_file_from_data, save_file_as_data
from app.utils.types import standard_responses
from app.utils.types.groups_type import GroupType
from app.utils.types.tags import Tags

router = APIRouter()


# ---------------------------------------------------------------------------- #
#                                    Get All                                   #
# ---------------------------------------------------------------------------- #
@router.get(
    "/phonebook/associations/",
    response_model=list[schemas_phonebook.AssociationComplete] | None,
    status_code=200,
    tags=[Tags.phonebook],
)
async def get_all_associations(
    db: AsyncSession = Depends(get_db),
):
    """
    Return all associations from database as a list of AssociationComplete schemas
    """
    return await cruds_phonebook.get_all_associations(db)


@router.get(
    "/phonebook/roletags/",
    response_model=schemas_phonebook.RoleTagsReturn | None,
    status_code=200,
    tags=[Tags.phonebook],
)
async def get_all_role_tags(
    db: AsyncSession = Depends(get_db),
    user=Depends(is_user_a_member_of(GroupType.CAA)),
):
    """
    Return all available role tags from database.

    **This endpoint is only usable by CAA**
    """
    roles = await cruds_phonebook.get_all_role_tags(db)
    roles_schema = schemas_phonebook.RoleTagsReturn(tags=roles)
    return roles_schema


@router.get(
    "/phonebook/associations/kinds",
    response_model=schemas_phonebook.KindsReturn | None,
    status_code=200,
    tags=[Tags.phonebook],
)
async def get_all_kinds(
    db: AsyncSession = Depends(get_db),
):
    """
    Return all available kinds of from database.

    **This endpoint is only usable by CAA**
    """
    kinds = await cruds_phonebook.get_all_kinds(db)
    kinds_schema = schemas_phonebook.KindsReturn(kinds=kinds)
    return kinds_schema


# ---------------------------------------------------------------------------- #
#                                  Association                                 #
# ---------------------------------------------------------------------------- #
@router.post(
    "/phonebook/associations/",
    response_model=schemas_phonebook.AssociationComplete,
    status_code=201,
    tags=[Tags.phonebook],
)
async def create_association(
    association: schemas_phonebook.AssociationBase,
    db: AsyncSession = Depends(get_db),
    user=Depends(is_user_a_member_of(GroupType.CAA)),
):
    """
    Create a new association by giving an AssociationBase scheme (contains the association name, desctription and type)

    **This endpoint is only usable by administrators**
    """
    id = str(uuid.uuid4())
    date = datetime.date.today()
    mandate_year = int(date.strftime("%Y"))  # Store the current mandate year
    association_model = models_phonebook.Association(
        id=id, mandate_year=mandate_year, **association.dict()
    )
    await cruds_phonebook.create_association(association_model, db)
    return association_model


@router.patch(
    "/phonebook/associations/{association_id}",
    # response_model=schemas_phonebook.AssociationComplete,
    status_code=204,
    tags=[Tags.phonebook],
)
async def update_association(
    association_id: str,
    association: schemas_phonebook.AssociationEditComplete,
    db: AsyncSession = Depends(get_db),
    user=Depends(is_user_a_member_of(GroupType.CAA)),
):
    """
    Update an association

    **This endpoint is only usable by CAA**
    """
    if association_id != association.id:
        raise HTTPException(
            status_code=404,
            detail="association_id and association's ID don't match",
        )
    await cruds_phonebook.update_association(association, db)


@router.delete(
    "/phonebook/associations/{association_id}",
    status_code=204,
    tags=[Tags.phonebook],
)
async def delete_association(
    association_id: str,
    db: AsyncSession = Depends(get_db),
    user=Depends(is_user_a_member_of(GroupType.CAA)),
):
    """
    Delete an association

    **This endpoint is only usable by CAA**
    """
    return await cruds_phonebook.delete_association(association_id, db)


# ---------------------------------------------------------------------------- #
#                                    Members                                   #
# ---------------------------------------------------------------------------- #
@router.get(
    "/phonebook/associations/{association_id}/members",
    response_model=list[schemas_phonebook.MemberComplete] | None,
    status_code=200,
    tags=[Tags.phonebook],
)
async def get_association_members(
    association_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get the list of memberships of an association."""
    memberships = await cruds_phonebook.get_mbmrships_by_association_id(
        association_id, db
    )
    members_complete = []
    if memberships is not None:
        for membership in memberships:
            association = await cruds_phonebook.get_association_by_id(
                membership.association_id, db
            )

            membership_base = schemas_phonebook.MembershipBase2Complete.from_orm(
                membership)
            membership_complete = schemas_phonebook.MembershipComplete(
                association=association,
                **membership_base.dict()
            )

            print("---->  ", membership_complete.dict())

            member = await cruds_phonebook.get_member_by_id(membership.user_id, db)
            member_schema = schemas_phonebook.MemberBase.from_orm(member)
            if association is None:
                continue
            if association.mandate_year == membership.mandate_year:
                members_complete.append(
                    schemas_phonebook.MemberComplete(
                        memberships=[membership_complete], **member_schema.dict()
                    )
                )

        return members_complete


# ---------------------------------------------------------------------------- #
#                                  Membership                                  #
# ---------------------------------------------------------------------------- #
@router.post(
    "/phonebook/associations/memberships",
    response_model=schemas_phonebook.MembershipComplete,
    status_code=201,
    tags=[Tags.phonebook],
)
async def create_membership(
    membership: schemas_phonebook.MembershipBase,
    db: AsyncSession = Depends(get_db),
    user=Depends(is_user_a_member_of(GroupType.CAA)),
):
    """
    Create a new membership for a given association, a given user. Tags are used to indicate if
    the members has a main role in the association (president, secretary ...) and
    'role_name' is the display name for this membership

    **This endpoint is only usable by CAA**
    """
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

    id = str(uuid.uuid4())
    mandate_year = association.mandate_year

    membership_model = models_phonebook.Membership(
        id=id,
        mandate_year=mandate_year,
        **membership.dict()
    )
    # Add the membership
    await cruds_phonebook.create_membership(membership_model, db)
    # Add the roletags to the attributed roletags table
    await cruds_phonebook.add_new_roles(role_tags, id, db)
    return schemas_phonebook.MembershipComplete(
        association=association,
        mandate_year=mandate_year,
        id=id,
        **membership.dict()
    )


@router.patch(
    "/phonebook/associations/memberships/{membership_id}",
    # response_model=schemas_phonebook.MembershipEdit,
    status_code=204,
    tags=[Tags.phonebook],
)
async def update_membership(
    membership: schemas_phonebook.MembershipEdit,
    membership_id: str,
    db: AsyncSession = Depends(get_db),
    user=Depends(is_user_a_member_of(GroupType.CAA)),
):
    """
    Update a membership.

    **This endpoint is only usable by CAA**
    """
    role_tags = dict(membership).pop("role_tags")
    if role_tags is not None:
        db_role_tags = await cruds_phonebook.get_membership_roletags(membership_id, db)
        for role in role_tags:
            if role not in db_role_tags:
                await cruds_phonebook.add_new_roles(role, membership_id, db)
        for role in db_role_tags:
            if role not in role_tags:
                await cruds_phonebook.delete_role(role, membership_id, db)
    membership_complete = schemas_phonebook.MembershipEdit(**membership.dict())
    await cruds_phonebook.update_membership(membership_complete, membership_id, db)


@router.delete(
    "/phonebook/associations/memberships/{membership_id}",
    # response_model=schemas_phonebook.MembershipBase,
    status_code=204,
    tags=[Tags.phonebook],
)
async def delete_membership(
    membership_id: str,
    db: AsyncSession = Depends(get_db),
    user=Depends(is_user_a_member_of(GroupType.CAA)),
):
    """
    Delete a membership.

    **This endpoint is only usable by CAA**
    """

    await cruds_phonebook.delete_role_tag(membership_id, db)
    await cruds_phonebook.delete_membership(membership_id, db)


# ---------------------------------------------------------------------------- #
#                                     Logos                                    #
# ---------------------------------------------------------------------------- #
@router.post(
    "/phonebook/associations/{association_id}/picture",
    # response_model=standard_responses.Result,
    status_code=201,
    tags=[Tags.phonebook],
)
async def create_association_logo(
    association_id: str,
    image: UploadFile = File(...),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.CAA)),
    request_id: str = Depends(get_request_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload a logo for an association.
    **The user must be a member of the group CAA to use this endpoint**
    """

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


@router.get(
    "/phonebook/associations/{association_id}/picture",
    response_class=FileResponse,
    status_code=200,
    tags=[Tags.users],
)
async def read_association_logo(
    association_id: str,
) -> FileResponse:
    """
    Get the logo of an association.
    """

    return get_file_from_data(
        directory="associations",
        filename=str(association_id) + ".png",
        default_asset=r"assets\images\default_association_picture.png",
    )
