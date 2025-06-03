"""File defining the functions called by the endpoints, making queries to the table using the models"""

import logging
import random
from collections.abc import Sequence

from fastapi import HTTPException
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.modules.raffle import models_raffle, schemas_raffle
from app.modules.raffle.types_raffle import RaffleStatusType

hyperion_error_logger = logging.getLogger("hyperion_error")


async def get_raffles(db: AsyncSession) -> Sequence[models_raffle.Raffle]:
    """Return all raffle from database"""

    result = await db.execute(
        select(models_raffle.Raffle).options(selectinload(models_raffle.Raffle.group)),
    )
    return result.scalars().all()


async def create_raffle(
    raffle: models_raffle.Raffle,
    db: AsyncSession,
) -> models_raffle.Raffle:
    """Create a new raffle in database and return it"""

    db.add(raffle)
    await db.flush()
    return raffle


async def get_raffles_by_groupid(
    group_id: str,
    db: AsyncSession,
) -> Sequence[models_raffle.Raffle]:
    result = await db.execute(
        select(models_raffle.Raffle).where(models_raffle.Raffle.group_id == group_id),
    )
    return result.scalars().all()


async def get_raffle_by_id(
    raffle_id: str,
    db: AsyncSession,
) -> models_raffle.Raffle | None:
    result = await db.execute(
        select(models_raffle.Raffle).where(models_raffle.Raffle.id == raffle_id),
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
        .values(**raffle_update.model_dump(exclude_none=True)),
    )
    await db.flush()


async def delete_raffle(
    db: AsyncSession,
    raffle_id: str,
):
    """Delete a raffle from database by id"""

    await db.execute(
        delete(models_raffle.Raffle).where(models_raffle.Raffle.id == raffle_id),
    )
    await db.flush()


async def get_prizes(db: AsyncSession) -> Sequence[models_raffle.Prize]:
    """Return all prizes from database"""

    result = await db.execute(
        select(models_raffle.Prize).options(selectinload(models_raffle.Prize.raffle)),
    )
    return result.scalars().all()


async def create_prize(
    prize: models_raffle.Prize,
    db: AsyncSession,
) -> models_raffle.Prize:
    """Create a new prize in databasend return it"""

    db.add(prize)
    await db.flush()
    return prize


async def get_prizes_by_raffleid(
    raffle_id: str,
    db: AsyncSession,
) -> Sequence[models_raffle.Prize]:
    result = await db.execute(
        select(models_raffle.Prize).where(models_raffle.Prize.raffle_id == raffle_id),
    )
    return result.scalars().all()


async def get_prize_by_id(
    prize_id: str,
    db: AsyncSession,
) -> models_raffle.Prize | None:
    result = await db.execute(
        select(models_raffle.Prize)
        .where(models_raffle.Prize.id == prize_id)
        .options(selectinload(models_raffle.Prize.raffle)),
    )
    return result.scalars().first()


async def edit_prize(
    prize_id: str,
    prize_update: schemas_raffle.PrizeEdit,
    db: AsyncSession,
):
    await db.execute(
        update(models_raffle.Prize)
        .where(models_raffle.Prize.id == prize_id)
        .values(**prize_update.model_dump(exclude_none=True)),
    )
    await db.flush()


async def delete_prize(
    db: AsyncSession,
    prize_id: str,
):
    """Delete a prize from database by id"""

    await db.execute(
        delete(models_raffle.Prize).where(models_raffle.Prize.id == prize_id),
    )
    await db.flush()


async def delete_prizes_by_raffleid(db: AsyncSession, raffle_id: str):
    """Delete prizes from database by raffle_id"""
    prizes_to_delete = await get_prizes_by_raffleid(raffle_id=raffle_id, db=db)
    await db.execute(
        delete(models_raffle.Prize).where(
            models_raffle.Prize.id.in_([prize.id for prize in prizes_to_delete]),
        ),
    )
    await db.flush()


async def get_packtickets(db: AsyncSession) -> Sequence[models_raffle.PackTicket]:
    """Return all packtickets from database"""

    result = await db.execute(
        select(models_raffle.PackTicket).options(
            selectinload(models_raffle.PackTicket.raffle),
        ),
    )
    return result.scalars().all()


async def create_packticket(
    packticket: models_raffle.PackTicket,
    db: AsyncSession,
) -> models_raffle.PackTicket:
    """Create a new Packticket in databasend return it"""

    db.add(packticket)
    await db.flush()
    return packticket


async def get_packtickets_by_raffleid(
    raffle_id: str,
    db: AsyncSession,
) -> Sequence[models_raffle.PackTicket]:
    result = await db.execute(
        select(models_raffle.PackTicket).where(
            models_raffle.PackTicket.raffle_id == raffle_id,
        ),
    )
    return result.scalars().all()


async def get_packticket_by_id(
    packticket_id: str,
    db: AsyncSession,
) -> models_raffle.PackTicket | None:
    result = await db.execute(
        select(models_raffle.PackTicket)
        .where(models_raffle.PackTicket.id == packticket_id)
        .options(selectinload(models_raffle.PackTicket.raffle)),
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
        .values(**packticket_update.model_dump(exclude_none=True)),
    )
    await db.flush()


async def delete_packticket(
    db: AsyncSession,
    packticket_id: str,
):
    """Delete a raffle from database by id"""

    await db.execute(
        delete(models_raffle.PackTicket).where(
            models_raffle.PackTicket.id == packticket_id,
        ),
    )
    await db.flush()


async def delete_packtickets_by_raffleid(db: AsyncSession, raffle_id: str):
    """Delete packtickets from database by raffle_id"""
    packtickets_to_delete = await get_packtickets_by_raffleid(
        raffle_id=raffle_id,
        db=db,
    )
    await db.execute(
        delete(models_raffle.PackTicket).where(
            models_raffle.PackTicket.id.in_([p.id for p in packtickets_to_delete]),
        ),
    )
    await db.flush()


async def get_tickets(db: AsyncSession) -> Sequence[models_raffle.Ticket]:
    """Return all tickets from database where raffle ID == raffle_id"""

    result = await db.execute(select(models_raffle.Ticket))
    return result.scalars().all()


async def create_ticket(
    tickets: Sequence[models_raffle.Ticket],
    db: AsyncSession,
) -> Sequence[models_raffle.Ticket]:
    """Create a new ticket in databasend return it"""
    db.add_all(tickets)
    await db.flush()
    return tickets


async def get_tickets_by_raffleid(
    raffle_id: str,
    db: AsyncSession,
) -> Sequence[models_raffle.Ticket]:
    results = (
        (
            await db.execute(
                select(models_raffle.Ticket).options(
                    joinedload(models_raffle.Ticket.pack_ticket).joinedload(
                        models_raffle.PackTicket.raffle,
                    ),
                    joinedload(models_raffle.Ticket.user),
                    joinedload(models_raffle.Ticket.prize),
                ),
            )
        )
        .scalars()
        .all()
    )
    return [result for result in results if result.pack_ticket.raffle_id == raffle_id]


async def get_ticket_by_id(
    ticket_id: str,
    db: AsyncSession,
) -> models_raffle.Ticket | None:
    result = await db.execute(
        select(models_raffle.Ticket).where(models_raffle.Ticket.id == ticket_id),
    )
    return result.scalars().first()


async def get_tickets_by_userid(
    user_id: str,
    db: AsyncSession,
) -> Sequence[models_raffle.Ticket]:
    result = await db.execute(
        select(models_raffle.Ticket)
        .where(models_raffle.Ticket.user_id == user_id)
        .options(
            joinedload(models_raffle.Ticket.pack_ticket).joinedload(
                models_raffle.PackTicket.raffle,
            ),
            joinedload(models_raffle.Ticket.user),
            joinedload(models_raffle.Ticket.prize),
        ),
    )
    return result.scalars().all()


async def delete_ticket(
    db: AsyncSession,
    ticket_id: str,
):
    """Delete a ticket from database by id"""

    await db.execute(
        delete(models_raffle.Ticket).where(models_raffle.Ticket.id == ticket_id),
    )
    await db.flush()


async def delete_tickets_by_raffleid(db: AsyncSession, raffle_id: str):
    """Delete tickets from database by raffle_id"""
    tickets_to_delete = await get_tickets_by_raffleid(raffle_id=raffle_id, db=db)
    await db.execute(
        delete(models_raffle.Ticket).where(
            models_raffle.Ticket.id.in_([t.id for t in tickets_to_delete]),
        ),
    )
    await db.flush()


async def get_users_cash(db: AsyncSession) -> Sequence[models_raffle.Cash]:
    result = await db.execute(
        select(models_raffle.Cash).options(selectinload(models_raffle.Cash.user)),
    )
    return result.scalars().all()


async def get_cash_by_id(db: AsyncSession, user_id: str) -> models_raffle.Cash | None:
    result = await db.execute(
        select(models_raffle.Cash)
        .where(models_raffle.Cash.user_id == user_id)
        .options(selectinload(models_raffle.Cash.user)),
    )
    return result.scalars().first()


async def create_cash_of_user(
    db: AsyncSession,
    cash: models_raffle.Cash,
) -> models_raffle.Cash:
    db.add(cash)
    await db.flush()
    return cash


async def edit_cash(db: AsyncSession, user_id: str, amount: float):
    await db.execute(
        update(models_raffle.Cash)
        .where(models_raffle.Cash.user_id == user_id)
        .values(user_id=user_id, balance=amount),
    )
    await db.flush()


async def draw_winner_by_prize_raffle(
    prize_id: str,
    db: AsyncSession,
) -> Sequence[models_raffle.Ticket]:
    prize = await get_prize_by_id(prize_id=prize_id, db=db)
    if prize is None:
        raise HTTPException(status_code=400, detail="Prize does not exist in db")
    raffle_id = prize.raffle_id

    gettickets = await get_tickets_by_raffleid(raffle_id=raffle_id, db=db)
    tickets = [t for t in gettickets if t.winning_prize is None]

    if len(tickets) < prize.quantity:
        winners = tickets

    else:
        winners = random.sample(tickets, prize.quantity)

    await db.execute(
        update(models_raffle.Ticket)
        .where(models_raffle.Ticket.id.in_([w.id for w in winners]))
        .values(winning_prize=prize_id),
    )
    await db.flush()

    await db.execute(
        update(models_raffle.Prize)
        .where(models_raffle.Prize.id == prize_id)
        .values(quantity=prize.quantity - len(winners)),
    )
    await db.flush()

    return winners


# Manage status


async def change_raffle_status(
    db: AsyncSession,
    raffle_id: str,
    status: RaffleStatusType,
):
    await db.execute(
        update(models_raffle.Raffle)
        .where(models_raffle.Raffle.id == raffle_id)
        .values(status=status),
    )
    await db.flush()
