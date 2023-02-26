"""File defining the functions called by the endpoints, making queries to the table using the models"""


import logging
from datetime import date

from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import noload, selectinload

from app.models import models_raffle
from app.schemas import schemas_raffle

hyperion_error_logger = logging.getLogger("hyperion_error")


# Raffles


async def get_raffles(db: AsyncSession) -> list[models_raffle.Raffle]:
    """Return all raffle from database"""

    result = await db.execute(select(models_raffle.Raffle))
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
    except IntegrityError:
        await db.rollback()
        raise ValueError("This name is already used")


async def get_raffle_by_id(
    raffle_id: int,
    db: AsyncSession,
) -> models_raffle.Raffle | None:
    result = await db.execute(
        select(models_raffle.Raffle).where(models_raffle.Raffle.id == raffle_id)
    )
    return result.scalars().first()


async def edit_raffle(
    raffle_id: int,
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


# Lots


async def get_lots(db: AsyncSession) -> list[models_raffle.Lots]:
    """Return all lots from database"""

    result = await db.execute(select(models_raffle.Lots))
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
    except IntegrityError:
        await db.rollback()
        raise ValueError("This name is already used")


async def get_lot_by_id(
    lot_id: int,
    db: AsyncSession,
) -> models_raffle.Lots | None:
    result = await db.execute(
        select(models_raffle.Lots).where(models_raffle.Lots.id == lot_id)
    )
    return result.scalars().first()


async def edit_lot(
    lot_id: int,
    lot_update: schemas_raffle.LotEdit,
    db: AsyncSession,
):
    await db.execute(
        update(models_raffle.Raffle)
        .where(models_raffle.Lots.id == lot_id)
        .values(**lot_update.dict(exclude_none=True))
    )
    await db.commit()


async def delete_lot(
    db: AsyncSession,
    lot_id: str,
):
    """Delete a raffle from database by id"""

    await db.execute(delete(models_raffle.Lots).where(models_raffle.Lots.id == lot_id))
    await db.commit()


# TypeTickets


async def get_typeticket(db: AsyncSession) -> list[models_raffle.TypeTicket]:
    """Return all typetickets from database"""

    result = await db.execute(select(models_raffle.TypeTicket))
    return result.scalars().all()


async def create_typeticket(
    typeticket: models_raffle.TypeTicket,
    db: AsyncSession,
) -> models_raffle.TypeTicket:
    """Create a new Typeticket in databasend return it"""

    db.add(typeticket)
    try:
        await db.commit()
        return typeticket
    except IntegrityError:
        await db.rollback()
        raise ValueError("This name is already used")


async def get_typeticket_by_id(
    typeticket_id: int,
    db: AsyncSession,
) -> models_raffle.TypeTicket | None:
    result = await db.execute(
        select(models_raffle.Lots).where(models_raffle.TypeTicket.id == typeticket_id)
    )
    return result.scalars().first()


async def edit_typeticket(
    typeticket_id: int,
    typeticket_update: schemas_raffle.LotEdit,
    db: AsyncSession,
):
    await db.execute(
        update(models_raffle.TypeTicket)
        .where(models_raffle.TypeTicket.id == typeticket_id)
        .values(**typeticket_update.dict(exclude_none=True))
    )
    await db.commit()


async def delete_typeticket(
    db: AsyncSession,
    typeticket_id: str,
):
    """Delete a raffle from database by id"""

    await db.execute(
        delete(models_raffle.TypeTicket).where(
            models_raffle.TypeTicket.id == typeticket_id
        )
    )
    await db.commit()


# Tickets


async def get_tickets(db: AsyncSession) -> list[models_raffle.Tickets]:
    """Return all tickets from database where raffle ID == raffle_id"""

    result = await db.execute(select(models_raffle.Tickets))
    return result.scalars().all()


async def create_ticket(
    ticket: models_raffle.Tickets,
    db: AsyncSession,
) -> models_raffle.Tickets:
    """Create a new ticket in databasend return it"""

    db.add(ticket)
    try:
        await db.commit()
        return ticket
    except IntegrityError:
        await db.rollback()
        raise ValueError("This name is already used")


async def get_ticket_by_id(
    ticket_id: int,
    db: AsyncSession,
) -> models_raffle.Tickets | None:
    result = await db.execute(
        select(models_raffle.Tickets).where(models_raffle.Tickets.id == ticket_id)
    )
    return result.scalars().first()


async def edit_ticket(
    ticket_id: int,
    ticket_update: schemas_raffle.TicketEdit,
    db: AsyncSession,
):
    await db.execute(
        update(models_raffle.Tickets)
        .where(models_raffle.Tickets.id == ticket_id)
        .values(**ticket_update.dict(exclude_none=True))
    )
    await db.commit()


async def delete_ticket(
    db: AsyncSession,
    ticket_id: str,
):
    """Delete a ticket from database by id"""

    await db.execute(
        delete(models_raffle.Tickets).where(models_raffle.Tickets.id == ticket_id)
    )
    await db.commit()


# Cash management


async def get_users_cash(db: AsyncSession) -> list[models_raffle.Cash]:
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
        raise ValueError(err)


async def add_cash(db: AsyncSession, user_id: str, amount: float):
    result = await db.execute(
        select(models_raffle.Cash).where(models_raffle.Cash.user_id == user_id)
    )
    balance = result.scalars().first()
    if balance is not None:
        await db.execute(
            update(models_raffle.Cash)
            .where(models_raffle.Cash.user_id == user_id)
            .values(user_id=balance.user_id, balance=balance.balance + amount)
        )
        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()
            raise ValueError("Error during cash edition")


async def remove_cash(db: AsyncSession, user_id: str, amount: float):
    result = await db.execute(
        select(models_raffle.Cash).where(models_raffle.Cash.user_id == user_id)
    )
    balance = result.scalars().first()
    if balance is not None:
        await db.execute(
            update(models_raffle.Cash)
            .where(models_raffle.Cash.user_id == user_id)
            .values(user_id=balance.user_id, balance=balance.balance - amount)
        )
        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()
            raise ValueError("Error during cash edition")
