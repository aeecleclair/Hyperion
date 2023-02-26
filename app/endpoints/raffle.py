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

    **The user must be an admin to use this endpoint**
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

    **The user must be a member of an admin to use this endpoint**
    """
    db_typeticket = models_raffle.TypeTicket(id=str(uuid.uuid4()), **typeticket.dict())

    try:
        result = await cruds_raffle.create_typeticket(typeticket=db_typeticket, db=db)
        return result
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))


# create a lot
@router.post(
    "/tombola/lot",
    response_model=schemas_raffle.LotEdit,
    status_code=201,
    tags=[Tags.raffle],
)
async def create_lot(
    lot: schemas_raffle.LotBase,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin)),
):
    """
    Create a new lot

    **The user must be an admin to use this endpoint**
    """
    db_lot = models_raffle.Lots(id=str(uuid.uuid4()), **lot.dict())

    try:
        result = await cruds_raffle.create_lot(lot=db_lot, db=db)
        return result
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))


# create a ticket
@router.post(
    "/tombola/ticket",
    response_model=schemas_raffle.TicketEdit,
    status_code=201,
    tags=[Tags.raffle],
)
async def create_ticket(
    ticket: schemas_raffle.TicketBase,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin)),
):
    """
    Create a new ticket

    **The user must be an admin to use this endpoint**
    """
    db_ticket = models_raffle.Tickets(id=str(uuid.uuid4()), **ticket.dict())

    try:
        result = await cruds_raffle.create_ticket(ticket=db_ticket, db=db)
        return result
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))


@router.get(
    "/tombola/raffle",
    response_model=list[schemas_raffle.RaffleComplete],
    status_code=200,
    tags=[Tags.raffle],
)
async def get_raffle(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin)),
):
    """
    Return all raffles

    **The user must be an admin to use this endpoint**
    """
    raffle = await cruds_raffle.get_raffles(db)
    return raffle


@router.get(
    "/tombola/tickets",
    response_model=list[schemas_raffle.TicketComplete],
    status_code=200,
    tags=[Tags.raffle],
)
async def get_tickets(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin)),
):
    """
    Return all tickets

    **The user must be an admin to use this endpoint**
    """
    tickets = await cruds_raffle.get_tickets(db)
    return tickets


@router.get(
    "/tombola/type_tickets",
    response_model=list[schemas_raffle.TypeTicketComplete],
    status_code=200,
    tags=[Tags.raffle],
)
async def get_type_tickets(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin)),
):
    """
    Return all tickets

    **The user must be an admin to use this endpoint**
    """
    tickets = await cruds_raffle.get_typeticket(db)
    return tickets


@router.get(
    "/tombola/lots",
    response_model=list[schemas_raffle.LotComplete],
    status_code=200,
    tags=[Tags.raffle],
)
async def get_lots(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin)),
):
    """
    Return all lots

    **The user must be an admin to use this endpoint**
    """
    lots = await cruds_raffle.get_lots(db)
    return lots


@router.get(
    "/amap/users/cash",
    response_model=list[schemas_raffle.CashComplete],
    status_code=200,
    tags=[Tags.raffle],
)
async def get_users_cash(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin)),
):
    """
    Get cash from all users.

    **The user must be a member of the group AMAP to use this endpoint**
    """
    cash = await cruds_raffle.get_users_cash(db)
    return cash
