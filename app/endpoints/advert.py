import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.cruds import cruds_advert
from app.dependencies import get_db, is_user_a_member, is_user_a_member_of
from app.models import models_advert, models_core
from app.schemas import schemas_advert
from app.utils.tools import (
    get_file_from_data,
    is_group_id_valid,
    is_user_id_valid,
    is_user_member_of_an_allowed_group,
    save_file_as_data,
)
from app.utils.types.groups_type import GroupType
from app.utils.types.tags import Tags

router = APIRouter()


@router.get(
    "/advert/adverts",
    response_model=list[schemas_advert.AdvertBase],
    status_code=200,
    tags=[Tags.loans],
)
async def read_loaners(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Get existing adverts
    """

    return await cruds_advert.get_adverts(db=db)


@router.get(
    "/advert/adverts/{advert_id}",
    response_model=schemas_advert.AdvertBase,
    status_code=200,
    tags=[Tags.loans],
)
async def read_loaners(
    advert_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Get an advert
    """

    return await cruds_advert.get_adverts(db=db)


@router.get(
    "/advert/adverts/{advert_id}/image",
    response_class=FileResponse,
    status_code=200,
    tags=[Tags.users],
)
async def read_session_poster(
    advert_id: str,
):
    """
    Get the image of an advert
    """
    return get_file_from_data(
        default_asset="assets/images/default_advert.png",
        directory="adverts",
        filename=str(advert_id),
    )
