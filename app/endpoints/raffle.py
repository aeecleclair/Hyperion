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


@router.patch(
    "/tombola/raffle/{raffle_id}",
    status_code=204,
    tags=[Tags.raffle],
)
async def edit_raffle(
    raffle_id: str,
    raffle_update: schemas_raffle.RaffleSimple,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin)),
):
    """
    Edit a raffle

    **The user must be an admin to use this endpoint**
    """

    raffle = await cruds_raffle.get_raffle_by_id(db=db, id=raffle_id)
    if not raffle:
        raise HTTPException(status_code=404, detail="Raffle not found")

    await cruds_raffle.edit_raffle(db=db, raffle_id=id, raffle_update=raffle_update)


async def delete_raffle(
    db: AsyncSession,
    raffle_id: str,
):
    """Delete a raffle from database by id"""

    await db.execute(
        delete(models_raffle.Raffle).where(models_raffle.Raffle.id == raffle_id)
    )
    await db.commit()


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


@router.patch(
    "/tombola/type_ticket/{raffle_id}",
    status_code=204,
    tags=[Tags.raffle],
)
async def edit_typeticket(
    typeticket_id: str,
    raffle_update: schemas_raffle.TypeTicketBase,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin)),
):
    """
    Edit a typeticket

    **The user must be an admin to use this endpoint**
    """

    raffle = await cruds_raffle.get_typeticket_by_id(db=db, id=typeticket_id)
    if not raffle:
        raise HTTPException(status_code=404, detail="Raffle not found")

    await cruds_raffle.edit_raffle(
        db=db, raffle_id=raffle_id, raffle_update=raffle_update
    )


async def delete_raffle(
    db: AsyncSession,
    raffle_id: str,
):
    """Delete a raffle from database by id"""

    await db.execute(
        delete(models_raffle.Raffle).where(models_raffle.Raffle.id == raffle_id)
    )
    await db.commit()


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
    "/tombola/users/cash",
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


@router.get(
    "/tombola/users/{user_id}/tickets",
    response_model=schemas_raffle.TicketComplete,
    status_code=200,
    tags=[Tags.raffle],
)
async def get_tickets_by_userid(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Get tickets from a specific user.

    """
    user_db = await cruds_users.get_user_by_id(db=db, user_id=user_id)
    if user_db is None:
        raise HTTPException(status_code=404, detail="User not found")

    if user_id == user.id or is_user_member_of_an_allowed_group(
        user, [GroupType.admin]
    ):
        ticket = await cruds_raffle.get_ticket_by_userid(user_id=user_id, db=db)
        if ticket is not None:
            return ticket

    else:
        raise HTTPException(
            status_code=403,
            detail="Users that are not member of the group admin can only access the endpoint for their own user_id.",
        )


@router.get(
    "/tombola/users/{user_id}/cash",
    response_model=schemas_raffle.CashComplete,
    status_code=200,
    tags=[Tags.raffle],
)
async def get_cash_by_id(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Get cash from a specific user.

    **The user must be a member of the group admin to use this endpoint or can only access the endpoint for its own user_id**
    """
    user_db = await cruds_users.get_user_by_id(db=db, user_id=user_id)
    if user_db is None:
        raise HTTPException(status_code=404, detail="User not found")

    if user_id == user.id or is_user_member_of_an_allowed_group(
        user, [GroupType.admin]
    ):
        cash = await cruds_raffle.get_cash_by_id(user_id=user_id, db=db)
        if cash is not None:
            return cash
        else:
            # We want to return a balance of 0 but we don't want to add it to the database
            # An admin AMAP has indeed to add a cash to the user the first time
            # TODO: this is a strange behaviour
            return schemas_raffle.CashComplete(balance=0, user_id=user_id, user=user_db)
    else:
        raise HTTPException(
            status_code=403,
            detail="Users that are not member of the group admin can only access the endpoint for their own user_id.",
        )


@router.post(
    "/tombola/users/{user_id}/cash",
    response_model=schemas_raffle.CashComplete,
    status_code=201,
    tags=[Tags.raffle],
)
async def create_cash_of_user(
    user_id: str,
    cash: schemas_raffle.CashEdit,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin)),
):
    """
    Create cash for an user.

    **The user must be a member of the group admin to use this endpoint**
    """

    user_db = await read_user(user_id=user_id, db=db)
    if not user_db:
        raise HTTPException(status_code=404, detail="User not found")

    existing_cash = await cruds_raffle.get_cash_by_id(db=db, user_id=user_id)
    if existing_cash is not None:
        raise HTTPException(
            status_code=400,
            detail="This user already has a cash.",
        )

    cash_db = models_raffle.Cash(user_id=user_id, balance=cash.balance)

    await cruds_raffle.create_cash_of_user(
        cash=cash_db,
        db=db,
    )

    # We can not directly return the cash_db because it does not contain the user.
    # Calling get_cash_by_id will return the cash with the user loaded as it's a relationship.
    return await cruds_raffle.get_cash_by_id(
        user_id=user_id,
        db=db,
    )


@router.patch(
    "/tombola/users/{user_id}/cash",
    status_code=204,
    tags=[Tags.raffle],
)
async def edit_cash_by_id(
    user_id: str,
    balance: schemas_raffle.CashEdit,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin)),
):
    """
    Edit cash for an user. This will add the balance to the current balance.
    A negative value can be provided to remove money from the user.

    **The user must be a member of the group AMAP to use this endpoint**
    """
    user_db = await read_user(user_id=user_id, db=db)
    if not user_db:
        raise HTTPException(status_code=404, detail="User not found")

    cash = await cruds_raffle.get_cash_by_id(db=db, user_id=user_id)
    if cash is None:
        raise HTTPException(
            status_code=404,
            detail="The user don't have a cash.",
        )

    await cruds_raffle.add_cash(user_id=user_id, amount=balance.balance, db=db)


@router.get(
    "/tombola/users/{user_id}/tickets",
    response_model=schemas_raffle.TicketComplete,
    status_code=200,
    tags=[Tags.raffle],
)
async def get_tickets_by_userid(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Get tickets from a specific user.

    """
    user_db = await cruds_users.get_user_by_id(db=db, user_id=user_id)
    if user_db is None:
        raise HTTPException(status_code=404, detail="User not found")

    if user_id == user.id or is_user_member_of_an_allowed_group(
        user, [GroupType.admin]
    ):
        ticket = await cruds_raffle.get_ticket_by_userid(user_id=user_id, db=db)
        if ticket is not None:
            return ticket

    else:
        raise HTTPException(
            status_code=403,
            detail="Users that are not member of the group admin can only access the endpoint for their own user_id.",
        )
