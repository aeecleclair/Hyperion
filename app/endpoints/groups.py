"""File defining the API itself, using fastAPI and schemas, and calling the cruds functions"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies import get_db
from app.cruds import cruds_groups
from app.schemas import schemas_core
from app.core.tags import Tags

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
    try:
        return await cruds_groups.create_group(group=group, db=db)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))


@router.delete("/groups/{group_id}", status_code=204, tags=[Tags.groups])
async def delete_group(group_id: int, db: AsyncSession = Depends(get_db)):
    """Delete group from database by id"""

    await cruds_groups.delete_group(db=db, group_id=group_id)
