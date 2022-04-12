"""File defining the API itself, using fastAPI and schemas, and calling the cruds functions"""

import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.cruds import cruds_groups
from app.dependencies import get_db
from app.schemas import schemas_core
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
async def read_group(group_id: int, db: AsyncSession = Depends(get_db)):
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


@router.delete("/groups/{group_id}", status_code=204, tags=[Tags.groups])
async def delete_group(group_id: int, db: AsyncSession = Depends(get_db)):
    """Delete group from database by id"""

    await cruds_groups.delete_group(db=db, group_id=group_id)


@router.post(
    "/groups/membership/{id_group}/{id_user}",
    response_model=schemas_core.CoreGroupSimple,
    status_code=201,
    tags=[Tags.groups],
)
async def create_membership(
    group: schemas_core.CoreGroup,
    id_group: int,
    id_user: int,
    db: AsyncSession = Depends(get_db),
):
    """Create a new membership in database and return the group as a dictionary"""
    try:
        return await cruds_groups.create_membership(
            db=db, id_group=id_group, id_user=id_user
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))
