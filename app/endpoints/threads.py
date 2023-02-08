from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.cruds import cruds_threads
from app.dependencies import get_db, is_user_a_member
from app.models import models_thread, models_core
from app.schemas import schemas_threads
from app.utils.types.tags import Tags

router = APIRouter()


@router.get(
    "/threads/me",
    response_model=list[schemas_threads.Thread],
    status_code=200,
    tags=[Tags.threads],
)
async def get_threads(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    return await cruds_threads.get_user_threads(db, user.id)
