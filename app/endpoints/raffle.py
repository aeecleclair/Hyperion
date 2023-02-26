import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Response
from pytz import timezone
from redis import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.cruds import cruds_raffle, cruds_users
from app.dependencies import (
    get_db,
    get_redis_client,
    get_settings,
    is_user_a_member,
    is_user_a_member_of,
)
from app.endpoints.users import read_user
from app.models import models_core, models_raffle
from app.schemas import schemas_raffle
from app.utils.redis import locker_get, locker_set
from app.utils.tools import is_user_member_of_an_allowed_group
from app.utils.types.amap_types import DeliveryStatusType
from app.utils.types.groups_type import GroupType
from app.utils.types.tags import Tags

router = APIRouter()


# create a raffle
@router.post(
    "/tombola/raffle",
    response_model=schemas_raffle.RaffleComplete,
    status_code=201,
    tags=[Tags.raffle],
)
async def create_raffle(
    raffle: schemas_raffle.RaffleSimple,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin)),
):
    """
    Create a new raffle

    **The user must be a member of a association to use this endpoint**
    """
    db_raffle = models_raffle.Raffle(id=str(uuid.uuid4()), **raffle.dict())

    try:
        result = await cruds_raffle.create_raffle(raffle=db_raffle, db=db)
        return result
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))


# create a typeticket
@router.post(
    "/tombola/type_ticket",
    response_model=schemas_raffle.TypeTicketComplete,
    status_code=201,
    tags=[Tags.raffle],
)
async def create_typeticket(
    typeticket: schemas_raffle.TypeTicketBase,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin)),
):
    """
    Create a new typeticket

    **The user must be a member of a association to use this endpoint**
    """
    db_typeticket = models_raffle.TypeTicket(id=str(uuid.uuid4()), **typeticket.dict())

    try:
        result = await cruds_raffle.create_typeticket(typeticket=db_typeticket, db=db)
        return result
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))


# création d'un nouveau lot
@router.post(
    "/tombola/type_ticket",
    response_model=schemas_raffle.LotComplete,
    status_code=201,
    tags=[Tags.raffle],
)
async def create_type_ticket(
    lot: schemas_raffle.LotBase,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.association)),
):
    """
    Create a new lot

    **The user must be a member of a association to use this endpoint**
    """
    db_lot = models_raffle.Lots(id=str(uuid.uuid4()), **lot.dict())

    try:
        result = await cruds_raffle.create_lot(product=db_lot, db=db)
        return result
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))


# création d'un nouveau type_ticket
@router.post(
    "/tombola/type_ticket",
    response_model=schemas_raffle.TypeTicketComplete,
    status_code=201,
    tags=[Tags.amap],
)
async def create_typeticket(
    typeticket: schemas_raffle.TypeTicketBase,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.association)),
):
    """
    Create a new typeticket

    **The user must be a member of the group AMAP to use this endpoint**
    """
    db_typeticket = models_raffle.TypeTicket(id=str(uuid.uuid4()), **typeticket.dict())

    try:
        result = await cruds_raffle.create_typeticket(product=db_typeticket, db=db)
        return result
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))
