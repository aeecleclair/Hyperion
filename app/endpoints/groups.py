from fastapi import APIRouter, Depends

# from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies import get_db
from app.cruds import cruds_groups
from app.schemas import schemas_core

router = APIRouter()


@router.get("/groups", response_model=list[schemas_core.CoreGroupBase])
async def get_groups(db: AsyncSession = Depends(get_db)):
    groups = await cruds_groups.get_groups(db)
    return groups
