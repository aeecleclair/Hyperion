import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.cruds import cruds_phonebook
from app.dependencies import get_db, get_request_id, is_user_a_member_of
from app.models import models_core
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
    "phonebook/associations/",
    response_model=list[schemas_phonebook.AssociationComplete],
    status_code=200,
    tags=[Tags.phonebook],
)
async def get_all_associations(
    db: AsyncSession = Depends(get_db),
):
    """
    Return all associations from database as a list of AssociationComplete schemas

    **This endpoint is only usable by administrators**
    """
    associations = await cruds_phonebook.get_all_associations(db)
    return associations


@router.get(
    "phonebook/roles/",
    response_model=list[schemas_phonebook.RoleComplete],
    status_code=200,
    tags=[Tags.phonebook],
)
async def get_all_roles(
    db: AsyncSession = Depends(get_db),
):
    """
    Return all roles from database as a list ofRoleComplete schemas

    **This endpoint is only usable by administrators**
    """
    roles = await cruds_phonebook.get_all_roles(db)
    return roles


# ---------------------------------------------------------------------------- #
#                                   Get by X ID                                #
# ---------------------------------------------------------------------------- #

# router get association/id --> infos de l'asso {id}


# ---------------------------------------------------------------------------- #
#                                  Association                                 #
# ---------------------------------------------------------------------------- #
@router.post(
    "phonebook/associations/",
    response_model=schemas_phonebook.AssociationComplete,
    status_code=200,
    tags=[Tags.phonebook],
)
async def create_association(
    association: schemas_phonebook.AssociationBase,
    db: AsyncSession = Depends(get_db),
    user=Depends(is_user_a_member_of(GroupType.CAA)),
):
    """
    Create a new association

    **This endpoint is only usable by administrators**
    """
    id = uuid.uuid4()
    association = schemas_phonebook.AssociationComplete(id=id, **association.dict())
    return await cruds_phonebook.create_association(association, db)


router.patch(
    "phonebook/associations/{association_id}",
    response_model=schemas_phonebook.AssociationComplete,
    status_code=200,
    tags=[Tags.phonebook],
)


async def update_association(
    association_id: str,
    association: schemas_phonebook.AssociationBase,
    db: AsyncSession = Depends(get_db),
    user=Depends(is_user_a_member_of(GroupType.CAA)),
):
    """
    Update an association

    **This endpoint is only usable by administrators**
    """
    return await cruds_phonebook.update_association(association_id, association, db)


router.delete(
    "phonebook/associations/{association_id}",
    status_code=200,
    tags=[Tags.phonebook],
)


async def delete_association(
    association_id: str,
    db: AsyncSession = Depends(get_db),
    user=Depends(is_user_a_member_of(GroupType.CAA)),
):
    """
    Delete an association

    **This endpoint is only usable by administrators**
    """
    return await cruds_phonebook.delete_association(association_id, db)


# ---------------------------------------------------------------------------- #
#                                    Members                                   #
# ---------------------------------------------------------------------------- #
router.get(
    "/phonebook/associations/id/members",
    response_model=schemas_phonebook.MemberComplete,
    status_code=200,
    tags=[Tags.phonebook],
)


async def get_member_mandates(
    user_id: str,
    db: AsyncSession = Depends(get_db),
):
    memberships = await cruds_phonebook.get_membership_by_user_id(user_id, db)
    if memberships is not None:
        memberships_complete = []
        for membership in memberships:
            association = await cruds_phonebook.get_association_by_id(
                membership.association_id, db
            )
            role = await cruds_phonebook.get_role_by_id(membership.role_id, db)
            membership_base = schemas_phonebook.MembershipBase.from_orm(membership)
            memberships_complete.append(
                schemas_phonebook.MembershipComplete(
                    association=association, role=role, **membership_base.dict()
                )
            )

        return memberships_complete


# ---------------------------------------------------------------------------- #
#                                  Membership                                  #
# ---------------------------------------------------------------------------- #
router.post(
    "/phonebook/associations/memberships",
    response_model=schemas_phonebook.MembershipBase,
    status_code=200,
    tags=[Tags.phonebook],
)


async def create_membership(
    membership: schemas_phonebook.MembershipBase,
    db: AsyncSession = Depends(get_db),
    user=Depends(is_user_a_member_of(GroupType.CAA)),
):
    """
    Create a new membership

    **This endpoint is only usable by administrators**
    """
    return await cruds_phonebook.create_membership(membership, db)


router.delete(
    "/phonebook/associations/memberships",
    response_model=schemas_phonebook.MembershipBase,
    status_code=200,
    tags=[Tags.phonebook],
)


async def delete_membership(
    membership: schemas_phonebook.MembershipBase,
    db: AsyncSession = Depends(get_db),
    user=Depends(is_user_a_member_of(GroupType.CAA)),
):
    """
    Delete a membership

    **This endpoint is only usable by administrators**
    """
    return await cruds_phonebook.delete_membership(membership, db)


# ---------------------------------------------------------------------------- #
#                                     Role                                     #
# ---------------------------------------------------------------------------- #
@router.post(
    "phonebook/roles/",
    response_model=schemas_phonebook.RoleComplete,
    status_code=200,
    tags=[Tags.phonebook],
)
async def create_role(
    role: schemas_phonebook.RoleBase,
    db: AsyncSession = Depends(get_db),
    user=Depends(is_user_a_member_of(GroupType.admin)),
):
    """
    Create a new role

    **This endpoint is only usable by administrators**
    """
    role_id = uuid.uuid4()
    role_complete = schemas_phonebook.RoleComplete(id=role_id, **role.dict())
    return await cruds_phonebook.create_role(role_complete, db)


@router.patch(
    "phonebook/roles/{role_id}",
    response_model=schemas_phonebook.RoleComplete,
    status_code=200,
    tags=[Tags.phonebook],
)
async def update_role(
    role: schemas_phonebook.RoleComplete,
    db: AsyncSession = Depends(get_db),
):
    """
    Update a role

    **This endpoint is only usable by administrators**
    """

    return await cruds_phonebook.update_role(role, db)


router.delete(
    "phonebook/roles/{role_id}",
    response_model=schemas_phonebook.RoleBase,
    status_code=200,
    tags=[Tags.phonebook],
)


async def delete_role(
    role_id: str,
    db: AsyncSession = Depends(get_db),
    user=Depends(is_user_a_member_of(GroupType.admin)),
):
    """
    Delete a role by giving its ID

    **This endpoint is only usable by administrators**
    """
    return await cruds_phonebook.delete_role(role_id, db)


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
        filename=str(association_id),
        default_asset="assets/images/default_association_logo.png",
    )
