from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import noload, selectinload

from app.core.ticket import models_ticket


def create_ticket(
    db: AsyncSession,
    ticket: models_ticket.Ticket,
):
    db.add(ticket)


async def delete_ticket_of_user(
    db: AsyncSession,
    user_id: str,
    generator_ids: list[UUID],
):
    await db.execute(
        delete(models_ticket.Ticket).where(
            models_ticket.Ticket.user_id == user_id,
            models_ticket.Ticket.generator_id.in_(generator_ids),
        ),
    )


async def get_tickets_of_user(
    db: AsyncSession,
    user_id: str,
) -> Sequence[models_ticket.Ticket]:
    result = await db.execute(
        select(models_ticket.Ticket).where(models_ticket.Ticket.user_id == user_id),
    )
    return result.scalars().all()


async def get_ticket(
    db: AsyncSession,
    ticket_id: UUID,
) -> models_ticket.Ticket | None:
    result = await db.execute(
        select(models_ticket.Ticket).where(models_ticket.Ticket.id == ticket_id),
    )
    return result.scalars().first()


async def get_ticket_by_secret(
    db: AsyncSession,
    secret: UUID,
) -> models_ticket.Ticket | None:
    result = await db.execute(
        select(models_ticket.Ticket)
        .where(models_ticket.Ticket.secret == secret)
        .options(
            selectinload(models_ticket.Ticket.user),
        ),
    )
    return result.scalars().first()


async def scan_ticket(db: AsyncSession, ticket_id: UUID, scan: int, tags: str):
    await db.execute(
        update(models_ticket.Ticket)
        .where(
            models_ticket.Ticket.id == ticket_id,
        )
        .values(scan_left=scan, tags=tags.lower()),
    )


async def get_ticket_generator(
    db: AsyncSession,
    ticket_generator_id: UUID,
) -> models_ticket.TicketGenerator | None:
    result = await db.execute(
        select(models_ticket.TicketGenerator).where(
            models_ticket.TicketGenerator.id == ticket_generator_id,
        ),
    )
    return result.scalars().first()


def create_ticket_generator(db: AsyncSession, ticket: models_ticket.TicketGenerator):
    db.add(ticket)


async def delete_ticket_generator(db: AsyncSession, ticket_generator_id: UUID):
    await db.execute(
        delete(models_ticket.TicketGenerator).where(
            models_ticket.TicketGenerator.id == ticket_generator_id,
        ),
    )


async def delete_product_generated_tickets(db: AsyncSession, ticket_generator_id: UUID):
    await db.execute(
        delete(models_ticket.Ticket).where(
            models_ticket.Ticket.generator_id == ticket_generator_id,
        ),
    )


async def get_tickets_by_tag(
    db: AsyncSession,
    generator_id: UUID,
    tag: str,
) -> Sequence[models_ticket.Ticket]:
    result = await db.execute(
        select(models_ticket.Ticket)
        .where(
            models_ticket.Ticket.generator_id == generator_id,
            models_ticket.Ticket.tags.contains(tag.lower()),
        )
        .options(
            selectinload(models_ticket.Ticket.user),
        ),
    )

    return result.scalars().all()


async def get_tickets_by_generator(
    db: AsyncSession,
    generator_id: UUID,
) -> Sequence[models_ticket.Ticket]:
    result = await db.execute(
        select(models_ticket.Ticket)
        .where(models_ticket.Ticket.generator_id == generator_id)
        .options(  # We will only return tags so we won't load useless data
            noload(models_ticket.Ticket.user),
        ),
    )

    return result.scalars().all()
