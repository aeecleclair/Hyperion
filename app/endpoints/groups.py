from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies import get_db
from app.cruds import cruds_groups
from app.schemas import schemas_core

router = APIRouter()


@router.get("/groups", response_model=list[schemas_core.CoreGroupSimple])
async def get_groups(db: AsyncSession = Depends(get_db)):
    """Return all groups from database as a list of dictionaries"""

    groups = await cruds_groups.get_groups(db)
    return groups


@router.get("/groups/{group_id}", response_model=schemas_core.CoreGroup)
async def read_group(group_id: int, db: AsyncSession = Depends(get_db)):
    """Return group with id from database as a dictionary"""

    db_group = await cruds_groups.get_group_by_id(db=db, group_id=group_id)
    if db_group is None:
        raise HTTPException(status_code=404, detail="Group not found")
    return db_group


@router.post("/groups", response_model=schemas_core.CoreGroupSimple)
async def create_group(
    group: schemas_core.CoreGroupCreate, db: AsyncSession = Depends(get_db)
):
    """Create a new group in database and return it as a dictionary"""
    try:
        return await cruds_groups.create_group(group=group, db=db)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))


@router.delete("/groups/{group_id}")
async def delete_group(group_id: int, db: AsyncSession = Depends(get_db)):
    """Delete group from database by id"""

    return await cruds_groups.delete_group(db=db, group_id=group_id)
