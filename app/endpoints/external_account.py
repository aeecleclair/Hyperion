from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.cruds import cruds_external_account
from app.dependencies import get_db, is_user_a_member_of
from app.models import models_core
from app.utils.types.groups_type import GroupType
from app.utils.types.tags import Tags

router = APIRouter()


@router.get(
    "/external/",
    status_code=200,
    tags=[Tags.external_account],
)
async def disable_external_users(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin)),
):
    return await cruds_external_account.disable_external_accounts(db=db)
