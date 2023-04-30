"""File defining the functions called by the endpoints, making queries to the table using the models"""

import logging
import random
from typing import Sequence

from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.models import models_raffle
from app.schemas import schemas_raffle
from app.utils.types.raffle_types import RaffleStatusType

hyperion_error_logger = logging.getLogger("hyperion_error")


async def get_raffles(db: AsyncSession) -> Sequence[models_raffle.Raffle]:
    """Return all raffle from database"""

    result = await db.execute(
        select(models_raffle.Raffle).options(selectinload(models_raffle.Raffle.group))
    )
    return result.scalars().all()


async def create_raffle(
    raffle: models_raffle.Raffle,
    db: AsyncSession,
) -> models_raffle.Raffle:
    """Create a new raffle in database and return it"""

    db.add(raffle)
    try:
        await db.commit()
        return raffle
    except IntegrityError as err:
        await db.rollback()
        raise err


async def get_raffles_by_groupid(
    group_id: str,
    db: AsyncSession,
) -> list[models_raffle.Raffle] | None:
    result = await db.execute(
        select(models_raffle.Raffle).where(models_raffle.Raffle.group_id == group_id)
    )
    return result.scalars().all()


async def get_raffle_by_id(
    raffle_id: str,
    db: AsyncSession,
) -> models_raffle.Raffle | None:
    result = await db.execute(
        select(models_raffle.Raffle).where(models_raffle.Raffle.id == raffle_id)
    )
    return result.scalars().first()


async def edit_raffle(
    raffle_id: str,
    raffle_update: schemas_raffle.RaffleEdit,
    db: AsyncSession,
):
    await db.execute(
        update(models_raffle.Raffle)
        .where(models_raffle.Raffle.id == raffle_id)
        .values(**raffle_update.dict(exclude_none=True))
    )
    await db.commit()


async def delete_raffle(
    db: AsyncSession,
    raffle_id: str,
):
    """Delete a raffle from database by id"""

    await db.execute(
        delete(models_raffle.Raffle).where(models_raffle.Raffle.id == raffle_id)
    )
    await db.commit()


async def get_lots(db: AsyncSession) -> Sequence[models_raffle.Lots]:
    """Return all lots from database"""

    result = await db.execute(
        select(models_raffle.Lots).options(selectinload(models_raffle.Lots.raffle))
    )
    return result.scalars().all()


async def create_lot(
    lot: models_raffle.Lots,
    db: AsyncSession,
) -> models_raffle.Lots:
    """Create a new lot in databasend return it"""

    db.add(lot)
    try:
        await db.commit()
        return lot
    except IntegrityError as err:
        await db.rollback()
        raise err


async def get_lot_by_raffleid(
    raffle_id: str,
    db: AsyncSession,
) -> Sequence[models_raffle.Lots]:
    result = await db.execute(
        select(models_raffle.Lots).where(models_raffle.Lots.raffle_id == raffle_id)
    )
    return result.scalars().all()


async def get_lot_by_id(
    lot_id: str,
    db: AsyncSession,
) -> models_raffle.Lots | None:
    result = await db.execute(
        select(models_raffle.Lots)
        .where(models_raffle.Lots.id == lot_id)
        .options(selectinload(models_raffle.Lots.raffle))
    )
    return result.scalars().first()


async def edit_lot(
    lot_id: str,
    lot_update: schemas_raffle.LotEdit,
    db: AsyncSession,
):
    await db.execute(
        update(models_raffle.Lots)
        .where(models_raffle.Lots.id == lot_id)
        .values(**lot_update.dict(exclude_none=True))
    )
    await db.commit()


async def delete_lot(
    db: AsyncSession,
    lot_id: str,
):
    """Delete a lot from database by id"""

    await db.execute(delete(models_raffle.Lots).where(models_raffle.Lots.id == lot_id))
    await db.commit()


async def get_packtickets(db: AsyncSession) -> Sequence[models_raffle.PackTicket]:
    """Return all packtickets from database"""

    result = await db.execute(
        select(models_raffle.PackTicket).options(
            selectinload(models_raffle.PackTicket.raffle),
        )
    )
    return result.scalars().all()


async def create_packticket(
    packticket: models_raffle.PackTicket,
    db: AsyncSession,
) -> models_raffle.PackTicket:
    """Create a new Packticket in databasend return it"""

    db.add(packticket)
    try:
        await db.commit()
        return packticket
    except IntegrityError as err:
        await db.rollback()
        raise err


async def get_packtickets_by_raffleid(
    raffle_id: str,
    db: AsyncSession,
) -> Sequence[models_raffle.PackTicket] | None:
    result = await db.execute(
        select(models_raffle.PackTicket).where(
            models_raffle.PackTicket.raffle_id == raffle_id
        )
    )
    return result.scalars().all()


async def get_packticket_by_id(
    packticket_id: str,
    db: AsyncSession,
) -> models_raffle.PackTicket | None:
    result = await db.execute(
        select(models_raffle.PackTicket)
        .where(models_raffle.PackTicket.id == packticket_id)
        .options(selectinload(models_raffle.PackTicket.raffle))
    )
    return result.scalars().first()


async def edit_packticket(
    packticket_id: str,
    packticket_update: schemas_raffle.PackTicketEdit,
    db: AsyncSession,
):
    await db.execute(
        update(models_raffle.PackTicket)
        .where(models_raffle.PackTicket.id == packticket_id)
        .values(**packticket_update.dict(exclude_none=True))
    )
    await db.commit()


async def delete_packticket(
    db: AsyncSession,
    packticket_id: str,
):
    """Delete a raffle from database by id"""

    await db.execute(
        delete(models_raffle.PackTicket).where(
            models_raffle.PackTicket.id == packticket_id
        )
    )
    await db.commit()


async def get_tickets(db: AsyncSession) -> Sequence[models_raffle.Tickets]:
    """Return all tickets from database where raffle ID == raffle_id"""

    result = await db.execute(select(models_raffle.Tickets))
    return result.scalars().all()


async def create_ticket(
    tickets: list[models_raffle.Tickets],
    db: AsyncSession,
) -> Sequence[models_raffle.Tickets]:
    """Create a new ticket in databasend return it"""
    db.add_all(tickets)
    try:
        await db.commit()
        return tickets
    except IntegrityError as err:
        await db.rollback()
        raise err


async def get_ticket_by_raffleid(
    raffle_id: str,
    db: AsyncSession,
) -> Sequence[models_raffle.Tickets]:
    results = (
        (
            await db.execute(
                select(models_raffle.Tickets).options(
                    joinedload(models_raffle.Tickets.pack_ticket).joinedload(
                        models_raffle.PackTicket.raffle
                    ),
                    joinedload(models_raffle.Tickets.user),
                    joinedload(models_raffle.Tickets.lot),
                )
            )
        )
        .scalars()
        .all()
    )
    filtered_results = [
        result for result in results if result.pack_ticket.raffle_id == raffle_id
    ]
    return filtered_results


async def get_ticket_by_id(
    ticket_id: str,
    db: AsyncSession,
) -> models_raffle.Tickets | None:
    result = await db.execute(
        select(models_raffle.Tickets).where(models_raffle.Tickets.id == ticket_id)
    )
    return result.scalars().first()


async def get_ticket_by_userid(
    user_id: str,
    db: AsyncSession,
) -> Sequence[models_raffle.Tickets] | None:
    result = await db.execute(
        select(models_raffle.Tickets)
        .where(models_raffle.Tickets.user_id == user_id)
        .options(
            joinedload(models_raffle.Tickets.pack_ticket).joinedload(
                models_raffle.PackTicket.raffle
            ),
            joinedload(models_raffle.Tickets.user),
            joinedload(models_raffle.Tickets.lot),
        )
    )
    return result.scalars().all()


async def delete_ticket(
    db: AsyncSession,
    ticket_id: str,
):
    """Delete a ticket from database by id"""

    await db.execute(
        delete(models_raffle.Tickets).where(models_raffle.Tickets.id == ticket_id)
    )
    await db.commit()


async def get_users_cash(db: AsyncSession) -> Sequence[models_raffle.Cash]:
    result = await db.execute(
        select(models_raffle.Cash).options(selectinload(models_raffle.Cash.user))
    )
    return result.scalars().all()


async def get_cash_by_id(db: AsyncSession, user_id: str) -> models_raffle.Cash | None:
    result = await db.execute(
        select(models_raffle.Cash)
        .where(models_raffle.Cash.user_id == user_id)
        .options(selectinload(models_raffle.Cash.user))
    )
    return result.scalars().first()


async def create_cash_of_user(
    db: AsyncSession, cash: models_raffle.Cash
) -> models_raffle.Cash:
    db.add(cash)
    try:
        await db.commit()
        return cash
    except IntegrityError as err:
        await db.rollback()
        raise err


async def edit_cash(db: AsyncSession, user_id: str, amount: float):
    await db.execute(
        update(models_raffle.Cash)
        .where(models_raffle.Cash.user_id == user_id)
        .values(user_id=user_id, balance=amount)
    )
    try:
        await db.commit()
    except IntegrityError as err:
        await db.rollback()
        raise ValueError(err)


async def draw_winner_by_lot_raffle(
    lot_id: str, db: AsyncSession
) -> Sequence[models_raffle.Tickets]:
    lot = await get_lot_by_id(lot_id=lot_id, db=db)
    if lot is None:
        raise ValueError("Invalid lot")
    raffle_id = lot.raffle_id

    if raffle_id is None:
        raise ValueError("Invalid raffle_id")

    gettickets = await get_ticket_by_raffleid(raffle_id=raffle_id, db=db)
    tickets = [t for t in gettickets if t.winning_lot is None]

    if len(tickets) < lot.quantity:
        winners = tickets

    else:
        winners = random.sample(tickets, lot.quantity)

    await db.execute(
        update(models_raffle.Tickets)
        .where(models_raffle.Tickets.id.in_([w.id for w in winners]))
        .values(winning_lot=lot_id)
    )
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise ValueError("Error during edition of the winning tickets")

    await db.execute(
        update(models_raffle.Lots)
        .where(models_raffle.Lots.id == lot_id)
        .values(quantity=lot.quantity - len(winners))
    )
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise ValueError("Error during edition of the lot")

    return winners


# Manage status


async def change_raffle_status(
    db: AsyncSession, raffle_id: str, status: RaffleStatusType
):
    await db.execute(
        update(models_raffle.Raffle)
        .where(models_raffle.Raffle.id == raffle_id)
        .values(status=status)
    )
    await db.commit()
