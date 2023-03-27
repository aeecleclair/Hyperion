import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from redis import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.cruds import cruds_raffle, cruds_users
from app.dependencies import (
    get_db,
    get_redis_client,
    get_request_id,
    is_user_a_member,
    is_user_a_member_of,
)
from app.endpoints.users import read_user
from app.models import models_core, models_raffle
from app.schemas import schemas_raffle
from app.utils.redis import locker_get, locker_set
from app.utils.tools import is_user_member_of_an_allowed_group
from app.utils.types.groups_type import GroupType
from app.utils.types.tags import Tags

router = APIRouter()
hyperion_raffle_logger = logging.getLogger("hyperion.raffle")


@router.get(
    "/tombola/raffles",
    response_model=list[schemas_raffle.RaffleComplete],
    status_code=200,
    tags=[Tags.raffle],
)
async def get_raffle(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Return all raffles
    """
    raffle = await cruds_raffle.get_raffles(db)
    return raffle


@router.post(
    "/tombola/raffles",
    response_model=schemas_raffle.RaffleComplete,
    status_code=201,
    tags=[Tags.raffle],
)
async def create_raffle(
    raffle: schemas_raffle.RaffleSimple,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.soli)),
):
    """
    Create a new raffle

    **The user must be a member of the group soli to use this endpoint**
    """
    db_raffle = models_raffle.Raffle(id=str(uuid.uuid4()), **raffle.dict())

    try:
        result = await cruds_raffle.create_raffle(raffle=db_raffle, db=db)
        return result
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))


@router.patch(
    "/tombola/raffles/{raffle_id}",
    status_code=204,
    tags=[Tags.raffle],
)
async def edit_raffle(
    raffle_id: str,
    raffle_update: schemas_raffle.RaffleEdit,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.soli)),
):
    """
    Edit a raffle

    **The user must be a member of the group soli to use this endpoint**
    """

    raffle = await cruds_raffle.get_raffle_by_id(raffle_id=raffle_id, db=db)
    if not raffle:
        raise HTTPException(status_code=404, detail="Raffle not found")

    await cruds_raffle.edit_raffle(
        raffle_id=raffle_id, raffle_update=raffle_update, db=db
    )


@router.delete(
    "/tombola/raffles/{raffle_id}",
    status_code=204,
    tags=[Tags.raffle],
)
async def delete_raffle(
    raffle_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.soli)),
):
    """
    Delete a raffle.

    **The user must be a member of the group soli to use this endpoint**
    """

    raffle = await cruds_raffle.get_raffle_by_id(raffle_id=raffle_id, db=db)
    if not raffle:
        raise HTTPException(status_code=404, detail="Raffle not found")

    await cruds_raffle.delete_raffle(raffle_id=raffle_id, db=db)


@router.get(
    "/tombola/group/{group_id}/raffles",
    response_model=list[schemas_raffle.RaffleComplete],
    status_code=200,
    tags=[Tags.raffle],
)
async def get_raffle_by_group_id(
    group_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Return all raffles from a group
    """
    raffle = await cruds_raffle.get_raffle_by_groupid(group_id, db)
    return raffle


# type tickets
@router.get(
    "/tombola/type_tickets",
    response_model=list[schemas_raffle.TypeTicketComplete],
    status_code=200,
    tags=[Tags.raffle],
)
async def get_type_tickets(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Return all tickets
    """
    type_tickets = await cruds_raffle.get_typeticket(db)
    return type_tickets


@router.post(
    "/tombola/type_tickets",
    response_model=schemas_raffle.TypeTicketComplete,
    status_code=201,
    tags=[Tags.raffle],
)
async def create_typeticket(
    typeticket: schemas_raffle.TypeTicketBase,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.soli)),
):
    """
    Create a new typeticket

    **The user must be a member of the group soli to use this endpoint**
    """
    db_typeticket = models_raffle.TypeTicket(id=str(uuid.uuid4()), **typeticket.dict())

    try:
        result = await cruds_raffle.create_typeticket(typeticket=db_typeticket, db=db)
        return result
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))


@router.patch(
    "/tombola/type_tickets/{typeticket_id}",
    status_code=204,
    tags=[Tags.raffle],
)
async def edit_typeticket(
    typeticket_id: str,
    typeticket_update: schemas_raffle.TypeTicketEdit,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.soli)),
):
    """
    Edit a typeticket

    **The user must be a member of the group soli to use this endpoint**
    """

    typeticket = await cruds_raffle.get_typeticket_by_id(
        typeticket_id=typeticket_id, db=db
    )
    if not typeticket:
        raise HTTPException(status_code=404, detail="TypeTicket not found")

    await cruds_raffle.edit_typeticket(
        typeticket_id=typeticket_id, typeticket_update=typeticket_update, db=db
    )


@router.delete(
    "/tombola/type_tickets/{typeticket_id}",
    status_code=204,
    tags=[Tags.raffle],
)
async def delete_typeticket(
    typeticket_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.soli)),
):
    """
    Delete a typeticket.

    **The user must be a member of the group soli to use this endpoint**
    """

    typeticket = await cruds_raffle.get_typeticket_by_id(
        typeticket_id=typeticket_id, db=db
    )
    if not typeticket:
        raise HTTPException(status_code=404, detail="Typeticket not found")

    await cruds_raffle.delete_typeticket(typeticket_id=typeticket_id, db=db)


@router.get(
    "/tombola/raffle/{raffle_id}/type_tickets",
    response_model=list[schemas_raffle.TypeTicketComplete],
    status_code=200,
    tags=[Tags.raffle],
)
async def get_type_tickets_by_raffle_id(
    raffle_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Return all type_tickets associated to a raffle
    """
    type_tickets = await cruds_raffle.get_typeticket_by_raffleid(raffle_id, db)
    return type_tickets


@router.get(
    "/tombola/tickets",
    response_model=list[schemas_raffle.TicketComplete],
    status_code=200,
    tags=[Tags.raffle],
)
async def get_tickets(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.soli)),
):
    """
    Return all tickets

    **The user must be a member of the group soli to use this endpoint**
    """
    tickets = await cruds_raffle.get_tickets(db)
    return tickets


@router.post(
    "/tombola/tickets/buy",
    response_model=schemas_raffle.TicketComplete,
    status_code=201,
    tags=[Tags.raffle],
)
async def buy_ticket(
    ticket: schemas_raffle.TicketBase,
    db: AsyncSession = Depends(get_db),
    redis_client: Redis | None = Depends(get_redis_client),
    user: models_core.CoreUser = Depends(is_user_a_member),
    request_id: str = Depends(get_request_id),
):
    """
    Buy a ticket
    """
    type_ticket = await cruds_raffle.get_typeticket_by_id(
        typeticket_id=ticket.type_id, db=db
    )
    if type_ticket is None:
        raise ValueError("Bad typeticket association")
    amount = ticket.nb_tickets * type_ticket.price

    balance: models_raffle.Cash | None = await cruds_raffle.get_cash_by_id(
        db=db,
        user_id=ticket.user_id,
    )

    # If the balance does not exist, we create a new one with a balance of 0
    if not balance:
        new_cash_db = schemas_raffle.CashDB(
            balance=0,
            user_id=ticket.user_id,
        )
        balance = models_raffle.Cash(
            **new_cash_db.dict(),
        )
        await cruds_raffle.create_cash_of_user(
            cash=balance,
            db=db,
        )
    db_ticket = models_raffle.Tickets(id=str(uuid.uuid4()), **ticket.dict())
    if not amount:
        raise HTTPException(status_code=403, detail="You can't buy nothing")

    redis_key = "raffle_" + ticket.user_id

    if not isinstance(redis_client, Redis) or locker_get(
        redis_client=redis_client, key=redis_key
    ):
        raise HTTPException(status_code=403, detail="Too fast !")
    locker_set(redis_client=redis_client, key=redis_key, lock=True)

    try:
        await cruds_raffle.create_ticket(ticket=db_ticket, db=db)
        await cruds_raffle.remove_cash(
            db=db,
            user_id=ticket.user_id,
            amount=amount,
        )

        hyperion_raffle_logger.info(
            f"Add_ticket_to_user: A ticket has been created for user {ticket.user_id} for an amount of {amount}€. ({request_id})"
        )

    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))

    finally:
        locker_set(redis_client=redis_client, key=redis_key, lock=False)


# @router.delete(
#     "/tombola/tickets/{ticket_id}",
#     status_code=204,
#     tags=[Tags.raffle],
# )
# async def delete_ticket(
#     ticket_id: str,
#     db: AsyncSession = Depends(get_db),
#     user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.soli)),
# ):
#     """
#     Delete a ticket.

#     **The user must be a member of the group soli to use this endpoint**
#     """

#     ticket = await cruds_raffle.get_ticket_by_id(ticket_id=ticket_id, db=db)
#     if not ticket:
#         raise HTTPException(status_code=404, detail="Ticket not found")

#     await cruds_raffle.delete_ticket(db=db, ticket_id=ticket_id)


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
    Get tickets of a specific user.

    **Only admin users can get tickets of another user**
    """
    user_db = await cruds_users.get_user_by_id(db=db, user_id=user_id)
    if user_db is None:
        raise HTTPException(status_code=404, detail="User not found")

    if user_id == user.id or is_user_member_of_an_allowed_group(user, [GroupType.soli]):
        ticket = await cruds_raffle.get_ticket_by_userid(user_id=user_id, db=db)
        if ticket is not None:
            return ticket

    else:
        raise HTTPException(
            status_code=403,
            detail="Users that are not member of the group admin can only access the endpoint for their own user_id.",
        )


@router.get(
    "/tombola/raffle/{raffle_id}/tickets",
    response_model=list[schemas_raffle.TicketComplete],
    status_code=200,
    tags=[Tags.raffle],
)
async def get_tickets_by_raffleid(
    raffle_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.soli)),
):
    """
    Get tickets from a specific raffle.

    **The user must be a member of the group soli to use this endpoint
    """

    tickets = await cruds_raffle.get_ticket_by_raffleid(raffle_id=raffle_id, db=db)

    return tickets


@router.get(
    "/tombola/lots",
    response_model=list[schemas_raffle.LotComplete],
    status_code=200,
    tags=[Tags.raffle],
)
async def get_lots(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Return all lots
    """
    lots = await cruds_raffle.get_lots(db)
    return lots


@router.post(
    "/tombola/lots",
    response_model=schemas_raffle.LotEdit,
    status_code=201,
    tags=[Tags.raffle],
)
async def create_lot(
    lot: schemas_raffle.LotBase,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.soli)),
):
    """
    Create a new lot

    **The user must be a member of the group soli to use this endpoint
    """
    db_lot = models_raffle.Lots(id=str(uuid.uuid4()), **lot.dict())

    try:
        result = await cruds_raffle.create_lot(lot=db_lot, db=db)
        return result
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))


@router.patch(
    "/tombola/lots/{lot_id}",
    status_code=204,
    tags=[Tags.raffle],
)
async def edit_lot(
    lot_id: str,
    lot_update: schemas_raffle.LotEdit,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.soli)),
):
    """
    Edit a lot

    **The user must be a member of the group soli to use this endpoint
    """

    lot = await cruds_raffle.get_lot_by_id(lot_id=lot_id, db=db)
    if not lot:
        raise HTTPException(status_code=404, detail="Lot not found")

    await cruds_raffle.edit_lot(lot_id=lot_id, lot_update=lot_update, db=db)


@router.delete(
    "/tombola/lots/{lot_id}",
    status_code=204,
    tags=[Tags.raffle],
)
async def delete_lot(
    lot_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.soli)),
):
    """
    Delete a lot.

    **The user must be a member of the group soli to use this endpoint
    """

    lot = await cruds_raffle.get_lot_by_id(lot_id=lot_id, db=db)
    if not lot:
        raise HTTPException(status_code=404, detail="Lot not found")

    await cruds_raffle.delete_lot(db=db, lot_id=lot_id)


@router.get(
    "/tombola/raffle/{raffle_id}/lots",
    response_model=schemas_raffle.LotComplete,
    status_code=200,
    tags=[Tags.raffle],
)
async def get_lots_by_raffleid(
    raffle_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Get lots from a specific raffle.

    **The user must be a member of the group soli to use this endpoint
    """

    lot = await cruds_raffle.get_lot_by_raffleid(raffle_id=raffle_id, db=db)
    if lot is not None:
        return lot


@router.get(
    "/tombola/users/cash",
    response_model=list[schemas_raffle.CashComplete],
    status_code=200,
    tags=[Tags.raffle],
)
async def get_users_cash(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.soli)),
):
    """
    Get cash from all users.

    **The user must be a member of the group soli to use this endpoint
    """
    cash = await cruds_raffle.get_users_cash(db)
    return cash


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

    **The user must be a member of the group soli to use this endpoint or can only access the endpoint for its own user_id**
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
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.soli)),
):
    """
    Create cash for a user.

    **The user must be a member of the group soli to use this endpoint**
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
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.soli)),
):
    """
    Edit cash for an user. This will add the balance to the current balance.
    A negative value can be provided to remove money from the user.

    **The user must be a member of the group soli to use this endpoint**
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


@router.post(
    "/tombola/lots/{lot_id}/draw",
    response_model=list[schemas_raffle.TicketComplete],
    status_code=201,
    tags=[Tags.raffle],
)
async def draw_winner(
    lot_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.soli)),
):
    winning_tickets = await cruds_raffle.draw_winner_by_lot_raffle(lot_id=lot_id, db=db)
    return winning_tickets
