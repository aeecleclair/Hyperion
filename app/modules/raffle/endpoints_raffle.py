import logging
import uuid

from fastapi import Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from redis import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.core_endpoints import models_core
from app.core.groups import cruds_groups
from app.core.groups.groups_type import AccountType, GroupType
from app.core.users import cruds_users
from app.core.users.endpoints_users import read_user
from app.dependencies import (
    get_db,
    get_redis_client,
    get_request_id,
    is_user_a_member,
    is_user_in,
)
from app.modules.raffle import cruds_raffle, models_raffle, schemas_raffle
from app.modules.raffle.types_raffle import RaffleStatusType
from app.types import standard_responses
from app.types.content_type import ContentType
from app.types.module import Module
from app.utils.redis import locker_get, locker_set
from app.utils.tools import (
    get_display_name,
    get_file_from_data,
    is_user_member_of_any_group,
    save_file_as_data,
)

module = Module(
    root="tombola",
    tag="Raffle",
    default_allowed_account_types=[AccountType.student, AccountType.staff],
)

hyperion_raffle_logger = logging.getLogger("hyperion.raffle")
hyperion_error_logger = logging.getLogger("hyperion.error")


@module.router.get(
    "/tombola/raffles",
    response_model=list[schemas_raffle.RaffleComplete],
    status_code=200,
)
async def get_raffle(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Return all raffles
    """
    raffles = await cruds_raffle.get_raffles(db)
    return raffles


@module.router.post(
    "/tombola/raffles",
    response_model=schemas_raffle.RaffleComplete,
    status_code=201,
)
async def create_raffle(
    raffle: schemas_raffle.RaffleBase,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_in(GroupType.admin)),
):
    """
    Create a new raffle

    **The user must be a member of the group admin to use this endpoint**
    """
    group = await cruds_groups.get_group_by_id(group_id=raffle.group_id, db=db)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    raffle.status = RaffleStatusType.creation
    db_raffle = models_raffle.Raffle(id=str(uuid.uuid4()), **raffle.model_dump())

    result = await cruds_raffle.create_raffle(raffle=db_raffle, db=db)
    return result


@module.router.patch(
    "/tombola/raffles/{raffle_id}",
    status_code=204,
)
async def edit_raffle(
    raffle_id: str,
    raffle_update: schemas_raffle.RaffleEdit,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Edit a raffle

    **The user must be a member of the raffle's group to use this endpoint**
    """

    raffle = await cruds_raffle.get_raffle_by_id(raffle_id=raffle_id, db=db)
    if not raffle:
        raise HTTPException(status_code=404, detail="Raffle not found")

    if not is_user_member_of_any_group(user, [raffle.group_id]):
        raise HTTPException(
            status_code=403,
            detail=f"{user.id} user is unauthorized to manage the raffle {raffle_id}",
        )

    if not (raffle.status == RaffleStatusType.creation):
        raise HTTPException(
            status_code=400,
            detail=f"Raffle {raffle_id} is not in Creation Mode",
        )

    await cruds_raffle.edit_raffle(
        raffle_id=raffle_id,
        raffle_update=raffle_update,
        db=db,
    )


@module.router.delete(
    "/tombola/raffles/{raffle_id}",
    status_code=204,
)
async def delete_raffle(
    raffle_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Delete a raffle.

    **The user must be a member of the raffle's group to use this endpoint**
    """
    raffle = await cruds_raffle.get_raffle_by_id(raffle_id=raffle_id, db=db)
    if not raffle:
        raise HTTPException(status_code=404, detail="Raffle not found")

    if not is_user_member_of_any_group(user, [raffle.group_id]):
        raise HTTPException(
            status_code=403,
            detail=f"{user.id} user is unauthorized to manage the raffle {raffle_id}",
        )

    await cruds_raffle.delete_tickets_by_raffleid(db=db, raffle_id=raffle_id)

    await cruds_raffle.delete_packtickets_by_raffleid(db=db, raffle_id=raffle_id)

    await cruds_raffle.delete_prizes_by_raffleid(db=db, raffle_id=raffle_id)

    await cruds_raffle.delete_raffle(raffle_id=raffle_id, db=db)


@module.router.get(
    "/tombola/group/{group_id}/raffles",
    response_model=list[schemas_raffle.RaffleComplete],
    status_code=200,
)
async def get_raffles_by_group_id(
    group_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Return all raffles from a group
    """
    raffle = await cruds_raffle.get_raffles_by_groupid(group_id, db)
    return raffle


@module.router.get(
    "/tombola/raffles/{raffle_id}/stats",
    response_model=schemas_raffle.RaffleStats,
    status_code=200,
)
async def get_raffle_stats(
    raffle_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """Return the number of ticket sold and the total amount recollected for a raffle"""
    raffle = await cruds_raffle.get_raffle_by_id(db=db, raffle_id=raffle_id)
    if raffle is None:
        raise HTTPException(status_code=404, detail="Raffle not found")

    tickets = await cruds_raffle.get_tickets_by_raffleid(db=db, raffle_id=raffle_id)

    tickets_sold = len(tickets)
    amount_raised = sum(
        [ticket.pack_ticket.price / ticket.pack_ticket.pack_size for ticket in tickets],
    )

    return schemas_raffle.RaffleStats(
        tickets_sold=tickets_sold,
        amount_raised=amount_raised,
    )


@module.router.post(
    "/tombola/raffles/{raffle_id}/logo",
    response_model=standard_responses.Result,
    status_code=201,
)
async def create_current_raffle_logo(
    raffle_id: str,
    image: UploadFile = File(...),
    user: models_core.CoreUser = Depends(is_user_a_member),
    request_id: str = Depends(get_request_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload a logo for a specific raffle.

    **The user must be a member of the raffle's group to use this endpoint**
    """
    raffle = await cruds_raffle.get_raffle_by_id(raffle_id=raffle_id, db=db)
    if not raffle:
        raise HTTPException(status_code=404, detail="Raffle not found")

    if not is_user_member_of_any_group(user, [raffle.group_id]):
        raise HTTPException(
            status_code=403,
            detail=f"{user.id} user is unauthorized to manage the raffle {raffle_id}",
        )

    if not (raffle.status == RaffleStatusType.creation):
        raise HTTPException(
            status_code=400,
            detail=f"Raffle {raffle_id} is not in Creation Mode",
        )

    await save_file_as_data(
        upload_file=image,
        directory="raffle-pictures",
        filename=str(raffle_id),
        request_id=request_id,
        max_file_size=4 * 1024 * 1024,
        accepted_content_types=[
            ContentType.jpg,
            ContentType.png,
            ContentType.webp,
        ],
    )

    return standard_responses.Result(success=True)


@module.router.get(
    "/tombola/raffles/{raffle_id}/logo",
    response_class=FileResponse,
    status_code=200,
)
async def read_raffle_logo(
    raffle_id: str,
    user: models_core.CoreUser = Depends(is_user_a_member),
    db: AsyncSession = Depends(get_db),
):
    """
    Get the logo of a specific raffle.
    """
    raffle = await cruds_raffle.get_raffle_by_id(raffle_id=raffle_id, db=db)
    if not raffle:
        raise HTTPException(status_code=404, detail="Raffle not found")

    return get_file_from_data(
        directory="raffle-pictures",
        filename=str(raffle_id),
        default_asset="assets/images/default_raffle_logo.png",
    )


@module.router.get(
    "/tombola/pack_tickets",
    response_model=list[schemas_raffle.PackTicketSimple],
    status_code=200,
)
async def get_pack_tickets(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Return all tickets
    """
    pack_tickets = await cruds_raffle.get_packtickets(db)
    return pack_tickets


@module.router.post(
    "/tombola/pack_tickets",
    response_model=schemas_raffle.PackTicketSimple,
    status_code=201,
)
async def create_packticket(
    packticket: schemas_raffle.PackTicketBase,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Create a new packticket

    **The user must be a member of the raffle's group to use this endpoint**
    """
    raffle = await cruds_raffle.get_raffle_by_id(raffle_id=packticket.raffle_id, db=db)
    if not raffle:
        raise HTTPException(status_code=404, detail="Raffle not found")

    if not is_user_member_of_any_group(user, [raffle.group_id]):
        raise HTTPException(
            status_code=403,
            detail=f"{user.id} user is unauthorized to manage the raffle {packticket.raffle_id}",
        )

    db_packticket = models_raffle.PackTicket(
        id=str(uuid.uuid4()),
        **packticket.model_dump(),
    )

    result = await cruds_raffle.create_packticket(packticket=db_packticket, db=db)
    return result


@module.router.patch(
    "/tombola/pack_tickets/{packticket_id}",
    status_code=204,
)
async def edit_packticket(
    packticket_id: str,
    packticket_update: schemas_raffle.PackTicketEdit,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Edit a packticket

    **The user must be a member of the raffle's group to use this endpoint**
    """

    packticket = await cruds_raffle.get_packticket_by_id(
        packticket_id=packticket_id,
        db=db,
    )

    if not packticket:
        raise HTTPException(status_code=404, detail="PackTicket not found")

    raffle = await cruds_raffle.get_raffle_by_id(raffle_id=packticket.raffle_id, db=db)
    if not raffle:
        raise HTTPException(status_code=404, detail="Raffle not found")

    if not is_user_member_of_any_group(user, [raffle.group_id]):
        raise HTTPException(
            status_code=403,
            detail=f"{user.id} user is unauthorized to manage the raffle {packticket.raffle_id}",
        )

    if not (raffle.status == RaffleStatusType.creation):
        raise HTTPException(
            status_code=400,
            detail=f"Raffle {packticket.raffle_id} is not in Creation Mode",
        )

    await cruds_raffle.edit_packticket(
        packticket_id=packticket_id,
        packticket_update=packticket_update,
        db=db,
    )


@module.router.delete(
    "/tombola/pack_tickets/{packticket_id}",
    status_code=204,
)
async def delete_packticket(
    packticket_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Delete a packticket.

    **The user must be a member of the raffle's group to use this endpoint**
    """

    packticket = await cruds_raffle.get_packticket_by_id(
        packticket_id=packticket_id,
        db=db,
    )
    if not packticket:
        raise HTTPException(status_code=404, detail="Packticket not found")

    raffle = await cruds_raffle.get_raffle_by_id(raffle_id=packticket.raffle_id, db=db)
    if not raffle:
        raise HTTPException(status_code=404, detail="Raffle not found")

    if not is_user_member_of_any_group(user, [raffle.group_id]):
        raise HTTPException(
            status_code=403,
            detail=f"{user.id} user is unauthorized to manage the raffle {packticket.raffle_id}",
        )

    await cruds_raffle.delete_packticket(packticket_id=packticket_id, db=db)


@module.router.get(
    "/tombola/raffles/{raffle_id}/pack_tickets",
    response_model=list[schemas_raffle.PackTicketSimple],
    status_code=200,
)
async def get_pack_tickets_by_raffle_id(
    raffle_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Return all pack_tickets associated to a raffle
    """
    pack_tickets = await cruds_raffle.get_packtickets_by_raffleid(raffle_id, db)
    return pack_tickets


@module.router.get(
    "/tombola/tickets",
    response_model=list[schemas_raffle.TicketSimple],
    status_code=200,
)
async def get_tickets(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_in(GroupType.admin)),
):
    """
    Return all tickets

    **The user must be a member of the group admin to use this endpoint**
    """
    tickets = await cruds_raffle.get_tickets(db)
    return tickets


@module.router.post(
    "/tombola/tickets/buy/{pack_id}",
    response_model=list[schemas_raffle.TicketComplete],
    status_code=201,
)
async def buy_ticket(
    pack_id: str,
    db: AsyncSession = Depends(get_db),
    redis_client: Redis | None = Depends(get_redis_client),
    user: models_core.CoreUser = Depends(is_user_a_member),
    request_id: str = Depends(get_request_id),
):
    """
    Buy a ticket
    """
    pack_ticket = await cruds_raffle.get_packticket_by_id(packticket_id=pack_id, db=db)
    if pack_ticket is None:
        raise HTTPException(status_code=404, detail="Ticket type not found")

    balance: models_raffle.Cash | None = await cruds_raffle.get_cash_by_id(
        db=db,
        user_id=user.id,
    )

    # If the balance does not exist, we create a new one with a balance of 0
    if not balance:
        new_cash_db = schemas_raffle.CashDB(
            balance=0,
            user_id=user.id,
        )
        balance = models_raffle.Cash(
            **new_cash_db.dict(),
        )
        await cruds_raffle.create_cash_of_user(
            cash=balance,
            db=db,
        )
    db_ticket = [
        models_raffle.Ticket(id=str(uuid.uuid4()), pack_id=pack_id, user_id=user.id)
        for i in range(pack_ticket.pack_size)
    ]

    for ticket in db_ticket:
        ticket.user = user
        ticket.pack_ticket = pack_ticket

    redis_key = "raffle_" + user.id

    if not isinstance(redis_client, Redis) or locker_get(
        redis_client=redis_client,
        key=redis_key,
    ):
        raise HTTPException(status_code=429, detail="Too fast !")

    locker_set(redis_client=redis_client, key=redis_key, lock=True)

    try:
        new_amount = balance.balance - pack_ticket.price
        if new_amount < 0:
            raise HTTPException(status_code=400, detail="Not enough cash")

        tickets = await cruds_raffle.create_ticket(tickets=db_ticket, db=db)
        await cruds_raffle.edit_cash(
            db=db,
            user_id=user.id,
            amount=new_amount,
        )

        display_name = get_display_name(
            firstname=user.firstname,
            name=user.name,
            nickname=user.nickname,
        )
        hyperion_raffle_logger.info(
            f"Add_ticket_to_user: A pack of {pack_ticket.pack_size} tickets of type {pack_id} has been buyed by user {display_name}({user.id}) for an amount of {pack_ticket.price}€. ({request_id})",
        )

        return tickets

    finally:
        locker_set(redis_client=redis_client, key=redis_key, lock=False)


@module.router.get(
    "/tombola/users/{user_id}/tickets",
    response_model=list[schemas_raffle.TicketComplete],
    status_code=200,
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

    if not (user_id == user.id or is_user_member_of_any_group(user, [GroupType.admin])):
        raise HTTPException(
            status_code=403,
            detail="Users that are not member of the group admin can only access the endpoint for their own user_id.",
        )

    else:
        tickets = await cruds_raffle.get_tickets_by_userid(user_id=user_id, db=db)
        return tickets


@module.router.get(
    "/tombola/raffles/{raffle_id}/tickets",
    response_model=list[schemas_raffle.TicketComplete],
    status_code=200,
)
async def get_tickets_by_raffleid(
    raffle_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Get tickets from a specific raffle.

    **The user must be a member of the raffle's group to use this endpoint
    """

    tickets = await cruds_raffle.get_tickets_by_raffleid(raffle_id=raffle_id, db=db)
    raffle = await cruds_raffle.get_raffle_by_id(raffle_id=raffle_id, db=db)

    if not raffle:
        raise HTTPException(status_code=404, detail="Raffle not found")

    raffle = await cruds_raffle.get_raffle_by_id(raffle_id=raffle_id, db=db)
    if not raffle:
        raise HTTPException(status_code=404, detail="Raffle not found")

    if not is_user_member_of_any_group(user, [raffle.group_id]):
        raise HTTPException(
            status_code=403,
            detail=f"{user.id} user is unauthorized to manage the raffle {raffle_id}",
        )

    return tickets


@module.router.get(
    "/tombola/prizes",
    response_model=list[schemas_raffle.PrizeSimple],
    status_code=200,
)
async def get_prizes(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Return all prizes
    """
    prizes = await cruds_raffle.get_prizes(db)
    return prizes


@module.router.post(
    "/tombola/prizes",
    response_model=schemas_raffle.PrizeSimple,
    status_code=201,
)
async def create_prize(
    prize: schemas_raffle.PrizeBase,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Create a new prize

    **The user must be a member of the raffle's group to use this endpoint
    """
    raffle = await cruds_raffle.get_raffle_by_id(raffle_id=prize.raffle_id, db=db)
    if not raffle:
        raise HTTPException(status_code=404, detail="Raffle not found")

    if not is_user_member_of_any_group(user, [raffle.group_id]):
        raise HTTPException(
            status_code=403,
            detail=f"{user.id} user is unauthorized to manage the raffle {raffle.id}",
        )

    if not (raffle.status == RaffleStatusType.creation):
        raise HTTPException(
            status_code=400,
            detail=f"Raffle {raffle.id} is not in Creation Mode",
        )

    db_prize = models_raffle.Prize(id=str(uuid.uuid4()), **prize.model_dump())

    result = await cruds_raffle.create_prize(prize=db_prize, db=db)
    return result


@module.router.patch(
    "/tombola/prizes/{prize_id}",
    status_code=204,
)
async def edit_prize(
    prize_id: str,
    prize_update: schemas_raffle.PrizeEdit,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Edit a prize

    **The user must be a member of the group raffle's to use this endpoint
    """

    prize = await cruds_raffle.get_prize_by_id(prize_id=prize_id, db=db)
    if not prize:
        raise HTTPException(status_code=404, detail="Prize not found")

    raffle = await cruds_raffle.get_raffle_by_id(raffle_id=prize.raffle_id, db=db)

    if not raffle:
        raise HTTPException(status_code=404, detail="Raffle not found")

    if not is_user_member_of_any_group(user, [raffle.group_id]):
        raise HTTPException(
            status_code=403,
            detail=f"{user.id} user is unauthorized to manage the raffle {raffle.id}",
        )

    if not (raffle.status == RaffleStatusType.creation):
        raise HTTPException(
            status_code=400,
            detail=f"Raffle {raffle.id} is not in Creation Mode",
        )

    await cruds_raffle.edit_prize(prize_id=prize_id, prize_update=prize_update, db=db)


@module.router.delete(
    "/tombola/prizes/{prize_id}",
    status_code=204,
)
async def delete_prize(
    prize_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Delete a prize.

    **The user must be a member of the group raffle's to use this endpoint
    """

    prize = await cruds_raffle.get_prize_by_id(prize_id=prize_id, db=db)
    if not prize:
        raise HTTPException(status_code=404, detail="Prize not found")

    raffle = await cruds_raffle.get_raffle_by_id(raffle_id=prize.raffle_id, db=db)

    if not raffle:
        raise HTTPException(status_code=404, detail="Raffle not found")

    if not is_user_member_of_any_group(user, [raffle.group_id]):
        raise HTTPException(
            status_code=403,
            detail=f"{user.id} user is unauthorized to manage the raffle {raffle.id}",
        )

    await cruds_raffle.delete_prize(db=db, prize_id=prize_id)


@module.router.get(
    "/tombola/raffles/{raffle_id}/prizes",
    response_model=list[schemas_raffle.PrizeSimple],
    status_code=200,
)
async def get_prizes_by_raffleid(
    raffle_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Get prizes from a specific raffle.
    """

    prizes = await cruds_raffle.get_prizes_by_raffleid(raffle_id=raffle_id, db=db)

    return prizes


@module.router.post(
    "/tombola/prizes/{prize_id}/picture",
    response_model=standard_responses.Result,
    status_code=201,
)
async def create_prize_picture(
    prize_id: str,
    image: UploadFile = File(...),
    user: models_core.CoreUser = Depends(is_user_a_member),
    request_id: str = Depends(get_request_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload a logo for a specific prize.

    **The user must be a member of the raffle's group to use this endpoint**
    """
    prize = await cruds_raffle.get_prize_by_id(prize_id=prize_id, db=db)
    if not prize:
        raise HTTPException(status_code=404, detail="Prize not found")

    raffle = await cruds_raffle.get_raffle_by_id(raffle_id=prize.raffle_id, db=db)

    if not raffle:
        raise HTTPException(status_code=404, detail="Raffle not found")

    if not is_user_member_of_any_group(user, [raffle.group_id]):
        raise HTTPException(
            status_code=403,
            detail=f"{user.id} user is unauthorized to manage the raffle {raffle.id}",
        )

    if not (raffle.status == RaffleStatusType.creation):
        raise HTTPException(
            status_code=400,
            detail=f"Raffle {raffle.id} is not in Creation Mode",
        )

    await save_file_as_data(
        upload_file=image,
        directory="raffle-prize_pictures",
        filename=str(prize_id),
        request_id=request_id,
        max_file_size=4 * 1024 * 1024,
        accepted_content_types=[
            ContentType.jpg,
            ContentType.png,
            ContentType.webp,
        ],
    )

    return standard_responses.Result(success=True)


@module.router.get(
    "/tombola/prizes/{prize_id}/picture",
    response_class=FileResponse,
    status_code=200,
)
async def read_prize_logo(
    prize_id: str,
    user: models_core.CoreUser = Depends(is_user_a_member),
    db: AsyncSession = Depends(get_db),
):
    """
    Get the logo of a specific prize.
    """
    prize = await cruds_raffle.get_prize_by_id(prize_id=prize_id, db=db)
    if not prize:
        raise HTTPException(status_code=404, detail="Prize not found")

    return get_file_from_data(
        directory="raffle-prize_picture",
        filename=str(prize_id),
        default_asset="assets/images/default_prize_picture.png",
    )


@module.router.get(
    "/tombola/users/cash",
    response_model=list[schemas_raffle.CashComplete],
    status_code=200,
)
async def get_users_cash(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_in(GroupType.admin)),
):
    """
    Get cash from all users.

    **The user must be a member of the group admin to use this endpoint
    """
    cash = await cruds_raffle.get_users_cash(db)
    return cash


@module.router.get(
    "/tombola/users/{user_id}/cash",
    response_model=schemas_raffle.CashComplete,
    status_code=200,
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

    if user_id == user.id or is_user_member_of_any_group(
        user,
        [GroupType.admin],
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


@module.router.post(
    "/tombola/users/{user_id}/cash",
    response_model=schemas_raffle.CashComplete,
    status_code=201,
)
async def create_cash_of_user(
    user_id: str,
    cash: schemas_raffle.CashEdit,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_in(GroupType.admin)),
):
    """
    Create cash for a user.

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


@module.router.patch(
    "/tombola/users/{user_id}/cash",
    status_code=204,
)
async def edit_cash_by_id(
    user_id: str,
    balance: schemas_raffle.CashEdit,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_in(GroupType.admin)),
    redis_client: Redis = Depends(get_redis_client),
):
    """
    Edit cash for an user. This will add the balance to the current balance.
    A negative value can be provided to remove money from the user.

    **The user must be a member of the group admin to use this endpoint**
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

    redis_key = "raffle_" + user_id

    if not isinstance(redis_client, Redis) or locker_get(
        redis_client=redis_client,
        key=redis_key,
    ):
        raise HTTPException(status_code=403, detail="Too fast !")
    locker_set(redis_client=redis_client, key=redis_key, lock=True)

    try:
        await cruds_raffle.edit_cash(
            user_id=user_id,
            amount=cash.balance + balance.balance,
            db=db,
        )
    except ValueError:
        hyperion_error_logger.exception("Error in tombola edit_cash_by_id")
        raise HTTPException(status_code=400, detail="Error while editing cash.")

    finally:
        locker_set(redis_client=redis_client, key=redis_key, lock=False)


@module.router.post(
    "/tombola/prizes/{prize_id}/draw",
    response_model=list[schemas_raffle.TicketComplete],
    status_code=201,
)
async def draw_winner(
    prize_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    prize = await cruds_raffle.get_prize_by_id(db=db, prize_id=prize_id)
    if prize is None:
        raise HTTPException(status_code=404, detail="Invalid prize id")

    raffle = await cruds_raffle.get_raffle_by_id(raffle_id=prize.raffle_id, db=db)

    if not raffle:
        raise HTTPException(status_code=404, detail="Raffle not found")

    if not is_user_member_of_any_group(user, [raffle.group_id]):
        raise HTTPException(
            status_code=403,
            detail=f"{user.id} user is unauthorized to manage the raffle {raffle.id}",
        )

    if prize.raffle.status != RaffleStatusType.lock:
        raise HTTPException(
            status_code=400,
            detail="Raffle must be locked to draw a prize",
        )

    try:
        winning_tickets = await cruds_raffle.draw_winner_by_prize_raffle(
            prize_id=prize_id,
            db=db,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    for ticket in winning_tickets:
        ticket.prize = prize

    return winning_tickets


@module.router.patch(
    "/tombola/raffles/{raffle_id}/open",
    status_code=204,
)
async def open_raffle(
    raffle_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Open a raffle

    **The user must be a member of the raffle's group to use this endpoint**
    """

    raffle = await cruds_raffle.get_raffle_by_id(raffle_id=raffle_id, db=db)
    if not raffle:
        raise HTTPException(status_code=404, detail="Raffle not found")

    if raffle.status is not RaffleStatusType.creation:
        raise HTTPException(
            status_code=400,
            detail=f"You can't mark a raffle as open if it is not in creation mode. The current mode is {raffle.status}.",
        )

    if not is_user_member_of_any_group(user, [raffle.group_id]):
        raise HTTPException(
            status_code=403,
            detail=f"{user.id} user is unauthorized to manage the raffle {raffle_id}",
        )

    await cruds_raffle.change_raffle_status(
        db=db,
        raffle_id=raffle_id,
        status=RaffleStatusType.open,
    )


@module.router.patch(
    "/tombola/raffles/{raffle_id}/lock",
    status_code=204,
)
async def lock_raffle(
    raffle_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Lock a raffle

    **The user must be a member of the raffle's group to use this endpoint**
    """

    raffle = await cruds_raffle.get_raffle_by_id(raffle_id=raffle_id, db=db)
    if not raffle:
        raise HTTPException(status_code=404, detail="Raffle not found")

    if not (raffle.status == RaffleStatusType.open):
        raise HTTPException(
            status_code=400,
            detail=f"You can't mark a raffle as locked if it is not in open mode. The current mode is {raffle.status}.",
        )

    if not is_user_member_of_any_group(user, [raffle.group_id]):
        raise HTTPException(
            status_code=403,
            detail=f"{user.id} user is unauthorized to manage the raffle {raffle_id}",
        )

    await cruds_raffle.change_raffle_status(
        db=db,
        raffle_id=raffle_id,
        status=RaffleStatusType.lock,
    )
