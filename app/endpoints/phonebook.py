import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.cruds import cruds_phonebook
from app.dependencies import (
    get_db,
    get_request_id,
    is_user_a_member,
    is_user_a_member_of,
)
from app.models import models_core, models_phonebook
from app.schemas import schemas_phonebook
from app.utils.tools import get_file_from_data, save_file_as_data
from app.utils.types import standard_responses
from app.utils.types.groups_type import GroupType
from app.utils.types.phonebook_type import QueryType
from app.utils.types.tags import Tags

router = APIRouter()


# --------------------------------- Research --------------------------------- #
@router.get(
    "/phonebook/research/",
    response_model=list[schemas_phonebook.RequestUserReturn],
    status_code=200,
    tags=[Tags.phonebook],
)
async def request_users(
    query: str,
    db: AsyncSession = Depends(get_db),
    query_type: QueryType = QueryType.person,
    user: models_core.CoreUser = Depends(is_user_a_member),
) -> list[schemas_phonebook.RequestUserReturn] | None:
    """Research users in the database by name, role or association."""
    print(f"---> {query_type} : {query}")
    if query_type == QueryType.person:
        return await cruds_phonebook.get_member_by_name(db, query)

    if query_type == QueryType.role:
        return await cruds_phonebook.get_member_by_role(db, query)

    if query_type == QueryType.association:
        return await cruds_phonebook.get_member_by_association(db, query)
    print("Error: query_type not found")
    return None


# -------------------------------- Association ------------------------------- #
@router.post(
    "/phonebook/associations/",
    response_model=list[schemas_phonebook.AssociationComplete],
    status_code=200,
    tags=[Tags.phonebook],
)
async def create_association(
    name: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.CAA)),
):
    """Create an association.

    **The user must be a member of the group CAA to use this endpoint**

    """
    association = models_phonebook.Association(name=name, id=str(uuid.uuid4()))
    return await cruds_phonebook.add_association(db=db, association=association)


@router.delete(
    "phonebook/associations/",
    status_code=200,
    tags=[Tags.phonebook],
)
async def delete_association(
    association_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.CAA)),
):
    """Delete an association.

    **The user must be a member of the group CAA to use this endpoint**

    """
    association = cruds_phonebook.get_association_by_id(db, association_id)
    if association is None:
        raise HTTPException(status_code=404, detail="Association not found")

    return await cruds_phonebook.delete_association(db=db, id=association_id)


@router.patch(
    "/phonebook/associations/",
    response_model=schemas_phonebook.AssociationComplete,
    status_code=200,
    tags=[Tags.phonebook],
)
async def update_association(
    association_id: str,
    association_update: schemas_phonebook.AssociationEdit,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.CAA)),
):
    """Edit an association.

    **The user must be a member of the group CAA to use this endpoint**

    """
    association = cruds_phonebook.get_association_by_id(db, association_id)
    if association is None:
        raise HTTPException(status_code=404, detail="Association not found")

    return await cruds_phonebook.edit_association(
        db=db, association_update=association_update, id=association_id
    )


# ---------------------------------- Member ---------------------------------- #
@router.post(
    "/phonebook/members/",
    response_model=schemas_phonebook.AssociationMemberComplete,
    status_code=200,
    tags=[Tags.phonebook],
)
async def create_member(
    association_id: str,
    mandate_year: int,
    role_id: str,
    user_id: str,
    db: AsyncSession = Depends(get_db),
    requesting_user=Depends(is_user_a_member_of(GroupType.CAA)),
):
    """Create a member."""
    member_model = models_phonebook.Member(
        user_id=user_id,
        association_id=association_id,
        role_id=role_id,
        mandate_year=mandate_year,
        member_id=str(uuid.uuid4()),
    )
    return await cruds_phonebook.add_member(db=db, member=member_model)


@router.patch(
    "/phonebook/members/",
    response_model=list[schemas_phonebook.AssociationMemberComplete],
    status_code=200,
    tags=[Tags.phonebook],
)
async def update_member(
    member_update: schemas_phonebook.AssociationMemberEdit,
    member_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.CAA)),
):
    """Update the members of the phonebook."""
    member = cruds_phonebook.get_member_by_id(db, member_id)
    if member is None:
        raise HTTPException(status_code=404, detail="Member not found")

    return await cruds_phonebook.edit_member(db, member_update, member_id)


@router.delete(
    "/phonebook/members/",
    status_code=200,
    tags=[Tags.phonebook],
)
async def delete_member(
    member_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.CAA)),
):
    """Delete a member from the phonebook."""
    member = cruds_phonebook.get_member_by_id(db, member_id)
    if member is None:
        raise HTTPException(status_code=404, detail="Member not found")

    return await cruds_phonebook.delete_member(db, member_id)


# ----------------------------------- Role ----------------------------------- #
@router.post(
    "/phonebook/roles/",
    response_model=schemas_phonebook.RoleComplete,
    status_code=200,
    tags=[Tags.phonebook],
)
async def create_role(
    role_name: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.CAA)),
):
    """Create a role."""
    role = models_phonebook.Role(name=role_name, id=str(uuid.uuid4()))
    return await cruds_phonebook.create_role(db=db, role=role)


@router.patch(
    "/phonebook/roles/",
    response_model=list[schemas_phonebook.RoleComplete],
    status_code=200,
    tags=[Tags.phonebook],
)
async def update_role(
    role_id: str,
    role_update: schemas_phonebook.RoleEdit,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.CAA)),
):
    """Update a role."""
    return await cruds_phonebook.edit_role(db=db, role_update=role_update, id=role_id)


@router.delete(
    "/phonebook/roles/",
    status_code=200,
    tags=[Tags.phonebook],
)
async def delete_role(
    role_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.CAA)),
):
    """Delete a role."""
    return await cruds_phonebook.delete_role(db=db, id=role_id)


# ----------------------------------- Logos ---------------------------------- #


@router.post(
    "/phonebook/associations/{association_id}/logo/",
    response_model=standard_responses.Result,
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

    association = await cruds_phonebook.get_association_by_id(db, association_id)
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
    "/phonebook/associations/{association_id}/logo/",
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
