import uuid

from fastapi import APIRouter, Depends  # , File, HTTPException, UploadFile

# from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.cruds import cruds_phonebook
from app.dependencies import get_db, is_user_a_member_of  # , get_request_id

# from app.models import models_phonebook
from app.schemas import schemas_phonebook

# from app.utils.tools import (
#     fuzzy_search_association,
#     fuzzy_search_role,
#     get_file_from_data,
#     save_file_as_data,
# )
# from app.utils.types import standard_responses
from app.utils.types.groups_type import GroupType
from app.utils.types.tags import Tags

router = APIRouter()
"""
# ---------------------------------------------------------------------------- #
#                                   Endpoints                                  #
# ---------------------------------------------------------------------------- #
phonebook/association/{?filter=<filter>}
{} = optionnel
<filter>  ce qu'st en train de chercher le requéreur
--> liste des associations par ordre alphabétique qui contient filter> dans leur nom si celui ci n'est pas vide

phonebook/association/[id]/members
--> liste des membres de l'association sous le format completeMember


# ------------------------------------ Research ----------------------------------- #
"""


# ---------------------------------------------------------------------------- #
@router.get(
    "phonebook/research/association/",
    response_model=list[schemas_phonebook.AssociationComplete],
    status_code=200,
    tags=[Tags.phonebook],
)
async def get_all_associations(
    db: AsyncSession = Depends(get_db),
    user=Depends(is_user_a_member_of(GroupType.admin)),
):
    """
    Return all associations from database as a list of dictionaries

    **This endpoint is only usable by administrators**
    """
    associations = await cruds_phonebook.get_associations(db)
    return associations


@router.get(
    f"phonebook/research/association/?filter={filter}",
    response_model=list[schemas_phonebook.AssociationComplete],
    status_code=200,
    tags=[Tags.phonebook],
)
async def get_associations_by_query(filter, db: AsyncSession = Depends(get_db)):
    associations = await cruds_phonebook.get_associations_by_query(filter, db)
    return associations


@router.post(
    "phonebook/association/",
    response_model=schemas_phonebook.AssociationBase,
    status_code=200,
    tags=[Tags.phonebook],
)
async def create_association(
    association: schemas_phonebook.AssociationBase,
    db: AsyncSession = Depends(get_db),
    user=Depends(is_user_a_member_of(GroupType.admin)),
):
    """
    Create a new association

    **This endpoint is only usable by administrators**
    """
    return await cruds_phonebook.create_association(association, db)


router.delete(
    "phonebook/association/{association_id}",
    response_model=schemas_phonebook.AssociationBase,
    status_code=200,
    tags=[Tags.phonebook],
)


async def delete_association(association_id, db: AsyncSession = Depends(get_db)):
    """
    Delete an association

    **This endpoint is only usable by administrators**
    """
    return await cruds_phonebook.delete_association(association_id, db)


router.patch(
    "phonebook/association/{association_id}",
    response_model=schemas_phonebook.AssociationBase,
    status_code=200,
    tags=[Tags.phonebook],
)


async def update_association(
    association_id,
    association: schemas_phonebook.AssociationBase,
    db: AsyncSession = Depends(get_db),
):
    """
    Update an association

    **This endpoint is only usable by administrators**
    """
    return await cruds_phonebook.update_association(association_id, association, db)


@router.post(
    "phonebook/role",
    response_model=schemas_phonebook.Role,
    status_code=200,
    tags=[Tags.phonebook],
)
async def create_role(
    role: schemas_phonebook.Role,
    db: AsyncSession = Depends(get_db),
    user=Depends(is_user_a_member_of(GroupType.admin)),
):
    """
    Create a new role

    **This endpoint is only usable by administrators**
    """
    role_id = uuid.uuid4()
    role = schemas_phonebook.Role(id=role_id, **role.dict())
    return await cruds_phonebook.create_role(role, db)


# @router.get(
#     "/phonebook/research/associations/getall/",
#     response_model=list[schemas_phonebook.AssociationReturn],
#     status_code=200,
#     tags=[Tags.phonebook],
# )
# async def get_all_associations(
#     db: AsyncSession = Depends(get_db),
#     user=Depends(is_user_a_member_of(GroupType.admin)),
# ):
#     """
#     Return all associations from database as a list of dictionaries

#     **This endpoint is only usable by administrators**
#     """
#     associations = await cruds_phonebook.get_associations(db)
#     return associations


# @router.get(
#     "/phonebook/research/associations/",
#     response_model=list[schemas_phonebook.AssociationReturn],
#     status_code=200,
#     tags=[Tags.phonebook],
# )
# async def research_associations(
#     query: str,
#     db: AsyncSession = Depends(get_db),
#     user=Depends(is_user_a_member_of(GroupType.admin)),
# ):
#     """
#     Return all associations from database as a list of dictionaries

#     **This endpoint is only usable by administrators**
#     """
#     associations = await cruds_phonebook.get_associations(db)

#     return fuzzy_search_association(query, associations)


# @router.get(
#     "/phonebook/research/roles/getall/",
#     response_model=list[schemas_phonebook.RoleReturn],
#     status_code=200,
#     tags=[Tags.phonebook],
# )
# async def get_all_roles(
#     db: AsyncSession = Depends(get_db),
#     user=Depends(is_user_a_member_of(GroupType.admin)),
# ):
#     """
#     Return all roles from database as a list of dictionaries

#     """
#     roles = await cruds_phonebook.get_roles(db)
#     return roles


# @router.get(
#     "/phonebook/research/roles/",
#     response_model=list[schemas_phonebook.RoleReturn],
#     status_code=200,
#     tags=[Tags.phonebook],
# )
# async def research_member_by_role(
#     query: str,
#     db: AsyncSession = Depends(get_db),
#     user=Depends(is_user_a_member_of(GroupType.admin)),
# ):
#     """
#     Return all members from database as a list of dictionaries

#     """
#     roles = await cruds_phonebook.get_roles(db)
#     return fuzzy_search_role(query, roles)


# # ------------------------------------ Add ----------------------------------- #
# @router.post(
#     "/phonebook/add/association/",
#     status_code=201,
#     tags=[Tags.phonebook],
# )
# async def add_association(
#     association: schemas_phonebook.AssociationCreate,
#     db: AsyncSession = Depends(get_db),
#     user=Depends(is_user_a_member_of(GroupType.admin)),
# ):
#     """
#     Add an association to the database

#     **This endpoint is only usable by administrators**
#     """
#     return await cruds_phonebook.add_association(db, association)


# @router.post(
#     "/phonebook/add/role/",
#     status_code=201,
#     tags=[Tags.phonebook],
# )
# async def add_role(
#     role: schemas_phonebook.RoleCreate,
#     db: AsyncSession = Depends(get_db),
#     user=Depends(is_user_a_member_of(GroupType.admin)),
# ):
#     return await cruds_phonebook.add_role(db, role)


# @router.post(
#     "/phonebook/add/member/",
#     status_code=201,
#     tags=[Tags.phonebook],
# )
# async def add_member(
#     member: schemas_phonebook.MemberCreate, db: AsyncSession = Depends(get_db)
# ):
#     """
#     Add a member to the database

#     **This endpoint is only usable by administrators**
#     """
#     return await cruds_phonebook.add_member(db, member)


# # ---------------------------------- Delete ---------------------------------- #
# @router.delete(
#     "/phonebook/delete/association/{association_id}",
#     status_code=204,
#     tags=[Tags.phonebook],
# )
# async def delete_association(
#     association_id: uuid.UUID,
#     db: AsyncSession = Depends(get_db),
#     user=Depends(is_user_a_member_of(GroupType.admin)),
# ):
#     """
#     Delete an association from the database

#     **This endpoint is only usable by administrators**
#     """
#     return await cruds_phonebook.delete_association(db, association_id)


# router.delete(
#     "/phonebook/delete/role/{role_id}",
#     status_code=204,
#     tags=[Tags.phonebook],
# )


# async def delete_role(
#     role_id: uuid.UUID,
#     db: AsyncSession = Depends(get_db),
#     user=Depends(is_user_a_member_of(GroupType.admin)),
# ):
#     """
#     Delete a role from the database

#     **This endpoint is only usable by administrators**
#     """
#     return await cruds_phonebook.delete_role(db, role_id)


# # ----------------------------------- Edit ----------------------------------- #
# @router.patch(
#     "/phonebook/edit/association/{association_id}",
#     response_model=schemas_phonebook.AssociationBase,
#     status_code=200,
#     tags=[Tags.phonebook],
# )
# async def update_association(
#     association_id: str,
#     association: schemas_phonebook.AssociationEdit,
#     db: AsyncSession = Depends(get_db),
#     user=Depends(is_user_a_member_of(GroupType.admin)),
# ):
#     """
#     Update an association in the database

#     **This endpoint is only usable by administrators**
#     """
#     return await cruds_phonebook.update_association(db, association_id, association)


# @router.patch(
#     "/phonebook/edit/role/{role_id}",
#     response_model=schemas_phonebook.RoleBase,
#     status_code=200,
#     tags=[Tags.phonebook],
# )
# async def update_role(
#     role_id: str,
#     role: schemas_phonebook.RoleEdit,
#     db: AsyncSession = Depends(get_db),
#     user=Depends(is_user_a_member_of(GroupType.admin)),
# ):
#     """
#     Update a role in the database

#     **This endpoint is only usable by administrators**
#     """
#     return await cruds_phonebook.update_role(db, role_id, role)


# @router.patch(
#     "/phonebook/edit/member/{member_id}",
#     response_model=schemas_phonebook.MemberBase,
#     status_code=200,
#     tags=[Tags.phonebook],
# )
# async def update_member(
#     member_id: str,
#     member: schemas_phonebook.MemberEdit,
#     db: AsyncSession = Depends(get_db),
#     user=Depends(is_user_a_member_of(GroupType.admin)),
# ):
#     """
#     Update a member in the database

#     **This endpoint is only usable by administrators**
#     """
#     return await cruds_phonebook.update_member(db, member_id, member)


# # ----------------------------------- Logos ---------------------------------- #


# @router.post(
#     "/phonebook/associations/{association_id}/logo/",
#     # response_model=standard_responses.Result,
#     status_code=201,
#     tags=[Tags.phonebook],
# )
# async def create_association_logo(
#     association_id: str,
#     image: UploadFile = File(...),
#     user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.CAA)),
#     request_id: str = Depends(get_request_id),
#     db: AsyncSession = Depends(get_db),
# ):
#     """
#     Upload a logo for an association.
#     **The user must be a member of the group CAA to use this endpoint**
#     """

#     association = await cruds_phonebook.get_association_by_id(db, association_id)
#     if association is None:
#         raise HTTPException(
#             status_code=404,
#             detail="The association does not exist.",
#         )

#     await save_file_as_data(
#         image=image,
#         directory="associations",
#         filename=str(association_id),
#         request_id=request_id,
#         max_file_size=4 * 1024 * 1024,
#         accepted_content_types=["image/jpeg", "image/png", "image/webp"],
#     )

#     return standard_responses.Result(success=True)


# @router.get(
#     "/phonebook/associations/{association_id}/logo/",
#     response_class=FileResponse,
#     status_code=200,
#     tags=[Tags.users],
# )
# async def read_association_logo(
#     association_id: str,
# ) -> FileResponse:
#     """
#     Get the logo of an association.
#     """

#     return get_file_from_data(
#         directory="associations",
#         filename=str(association_id),
#         default_asset="assets/images/default_association_logo.png",
#     )
