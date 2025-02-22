import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.rPlace import cruds_rplace
from app.dependencies import get_db, is_user_a_member
from app.modules.rPlace import models_rplace
from app.modules.rPlace import schemas_rplace
from app.core.groups.groups_type import GroupType
from app.core import models_core
from app.types.module import Module

module = Module(
    root="rpalce",
    tag="rplace",
    default_allowed_groups_ids=[GroupType.student],
)


@module.router.get(
    "/rplace/pixels",
    response_model=list[schemas_rplace.Pixel],
    status_code=200,
)
async def get_pixels(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):

    return await cruds_rplace.get_pixels(db=db)

@module.router.post(
    "/rplace/pixels",
    response_model=schemas_rplace.Pixel,
    status_code=201,
)
async def create_pixel(
    pixel: schemas_rplace.Pixel,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    id = uuid.uuid4()
    

    db_item = models_rplace.Pixel(
        id = id,
        date=datetime.now(),
        user_id=user.id,
        x=pixel.x,
        y=pixel.y,
        color=pixel.color
    )
    try:
        res = await cruds_rplace.create_pixel(
            rplace_pixel=db_item,
            db=db,
        )
        return res
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))