from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies import get_db
from app.cruds import cruds_groups
from app.schemas import schemas_core

router = APIRouter()

""" Working """


@router.get("/groups", response_model=list[schemas_core.CoreGroupBase])
async def get_groups(db: AsyncSession = Depends(get_db)):
    groups = await cruds_groups.get_groups(db)
    return groups


@router.post("/groups", response_model=schemas_core.CoreGroupBase)
async def create_group(
    group: schemas_core.CoreGroupCreate, db: AsyncSession = Depends(get_db)
):
    try:
        return await cruds_groups.create_group(group=group, db=db)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))


# schemas_core.CoreUserBase)
# async def create_user(
#     user: schemas_core.CoreUserCreate, db: AsyncSession = Depends(get_db)
# ):
#     try:
#         return await cruds_users.create_user(user=user, db=db)
#     except ValueError as error:
#         raise HTTPException(status_code=422, detail=str(error))
