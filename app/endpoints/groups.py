"""File defining the API itself, using fastAPI and schemas, and calling the cruds functions"""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.cruds import cruds_groups
from app.dependencies import get_db
from app.schemas import schemas_core
from app.utils.types.account_type import AccountType
from app.utils.types.tags import Tags

router = APIRouter()


@router.get(
    "/groups/",
    response_model=list[schemas_core.CoreGroupSimple],
    status_code=200,
    tags=[Tags.groups],
)
async def get_groups(db: AsyncSession = Depends(get_db)):
    """Return all groups from database as a list of dictionaries"""

    groups = await cruds_groups.get_groups(db)
    return groups


@router.get(
    "/groups/{group_id}",
    response_model=schemas_core.CoreGroup,
    status_code=200,
    tags=[Tags.groups],
)
async def read_group(group_id: str, db: AsyncSession = Depends(get_db)):
    """Return group with id from database as a dictionary"""

    db_group = await cruds_groups.get_group_by_id(db=db, group_id=group_id)
    if db_group is None:
        raise HTTPException(status_code=404, detail="Group not found")
    return db_group


@router.post(
    "/groups/",
    response_model=schemas_core.CoreGroupSimple,
    status_code=201,
    tags=[Tags.groups],
)
async def create_group(
    group: schemas_core.CoreGroupCreate, db: AsyncSession = Depends(get_db)
):
    """Create a new group in database and return it as a dictionary"""
    db_group = schemas_core.CoreGroupInDB(id=str(uuid.uuid4()), **group.dict())
    try:
        return await cruds_groups.create_group(group=db_group, db=db)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))


@router.patch(
    "/groups/{group_id}",
    response_model=schemas_core.CoreGroup,
    tags=[Tags.groups],
)
async def update_group(
    group_id: str,
    group_update: schemas_core.CoreGroupUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update the name or the description of a group"""
    group = await cruds_groups.get_group_by_id(db=db, group_id=group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    await cruds_groups.update_group(db=db, group_id=group_id, group_update=group_update)

    return group


@router.delete("/groups/{group_id}", status_code=204, tags=[Tags.groups])
async def delete_group(group_id: str, db: AsyncSession = Depends(get_db)):
    """Delete group from database by id"""

    # TODO check if the client is admin
    if group_id in [id for id in AccountType]:
        raise HTTPException(status_code=422, detail="Account types can't be deleted")

    await cruds_groups.delete_group(db=db, group_id=group_id)


@router.post(
    "/groups/membership",
    response_model=schemas_core.CoreGroup,
    status_code=201,
    tags=[Tags.groups],
)
async def create_membership(
    membership: schemas_core.CoreMembership,
    db: AsyncSession = Depends(get_db),
):
    """Create a new membership in database and return the group as a dictionary"""
    try:
        return await cruds_groups.create_membership(db=db, membership=membership)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))
