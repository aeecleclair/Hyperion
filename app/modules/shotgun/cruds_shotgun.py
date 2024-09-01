from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.shotgun import models_shotgun


async def get_organizers(db: AsyncSession) -> Sequence[models_shotgun.ShotgunOrganizer]:
    result = await db.execute(select(models_shotgun.ShotgunOrganizer))
    return result.scalars().all()


async def get_organizers_by_group_ids(
    db: AsyncSession,
    group_ids: list[str],
) -> Sequence[models_shotgun.ShotgunOrganizer]:
    result = await db.execute(
        select(models_shotgun.ShotgunOrganizer).where(
            models_shotgun.ShotgunOrganizer.group_id.in_(group_ids),
        ),
    )
    return result.scalars().all()


async def get_organizer_by_id(
    db: AsyncSession,
    organizer_id: UUID,
) -> models_shotgun.ShotgunOrganizer | None:
    result = await db.execute(
        select(models_shotgun.ShotgunOrganizer).where(
            models_shotgun.ShotgunOrganizer.id == organizer_id,
        ),
    )
    return result.scalars().first()


def create_organizer(db: AsyncSession, organizer: models_shotgun.ShotgunOrganizer):
    db.add(organizer)


async def delete_organizer(db: AsyncSession, organizer_id: UUID):
    await db.execute(
        select(models_shotgun.ShotgunOrganizer).where(
            models_shotgun.ShotgunOrganizer.id == organizer_id,
        ),
    )


async def get_sessions(db: AsyncSession) -> Sequence[models_shotgun.ShotgunSession]:
    result = await db.execute(select(models_shotgun.ShotgunSession))
    return result.scalars().all()


async def get_sessions_by_organizer_id(
    db: AsyncSession,
    organizer_id: UUID,
) -> Sequence[models_shotgun.ShotgunSession]:
    result = await db.execute(
        select(models_shotgun.ShotgunSession).where(
            models_shotgun.ShotgunSession.organizer_id == organizer_id,
        ),
    )
    return result.scalars().all()


def create_session(db: AsyncSession, session: models_shotgun.ShotgunSession):
    db.add(session)


async def get_purchase_by_id(
    db: AsyncSession,
    purchase_id: UUID,
) -> models_shotgun.ShotgunPurchase | None:
    result = await db.execute(
        select(models_shotgun.ShotgunPurchase).where(
            models_shotgun.ShotgunPurchase.id == purchase_id,
        ),
    )
    return result.scalars().first()


async def mark_purchase_as_paid(db: AsyncSession, purchase_id: UUID):
    await db.execute(
        update(models_shotgun.ShotgunPurchase)
        .where(models_shotgun.ShotgunPurchase.id == purchase_id)
        .values(paid=True),
    )


async def get_session_by_id(
    db: AsyncSession,
    session_id: UUID,
) -> models_shotgun.ShotgunSession | None:
    await db.execute(
        select(models_shotgun.ShotgunSession)
        .where(
            models_shotgun.ShotgunSession.id == session_id,
        )
        .with_for_update(),
    )
    result_outdated_purchases = await db.execute(
        delete(models_shotgun.ShotgunPurchase).where(
            models_shotgun.ShotgunPurchase.session_id == session_id,
            models_shotgun.ShotgunPurchase.paid.is_(False),
            models_shotgun.ShotgunPurchase.purchased_on + timedelta(minutes=16)
            > datetime.now(UTC),
        ),
    )
    await db.execute(
        update(models_shotgun.ShotgunSession)
        .where(models_shotgun.ShotgunSession.id == session_id)
        .values(
            quantity=models_shotgun.ShotgunSession.quantity
            + result_outdated_purchases.rowcount,
        ),
    )
    await db.commit()
    result = await db.execute(
        select(models_shotgun.ShotgunSession).where(
            models_shotgun.ShotgunSession.id == session_id,
        ),
    )
    return result.scalars().first()


async def get_session_generators(
    db: AsyncSession,
    session_id: UUID,
) -> Sequence[models_shotgun.ShotgunTicketGenerator]:
    result = await db.execute(
        select(models_shotgun.ShotgunTicketGenerator).where(
            models_shotgun.ShotgunTicketGenerator.session_id == session_id,
        ),
    )
    return result.scalars().all()


async def get_session_tickets(
    db: AsyncSession,
    session_id: UUID,
) -> Sequence[models_shotgun.ShotgunTicket]:
    result = await db.execute(
        select(models_shotgun.ShotgunTicket).where(
            models_shotgun.ShotgunTicket.session_id == session_id,
        ),
    )
    return result.scalars().all()


async def delete_session(db: AsyncSession, session_id: UUID):
    """Delete a session, with all its tickets and generators"""
    await db.execute(
        delete(models_shotgun.ShotgunSession).where(
            models_shotgun.ShotgunSession.id == session_id,
        ),
    )
    await db.execute(
        delete(models_shotgun.ShotgunTicket).where(
            models_shotgun.ShotgunTicket.session_id == session_id,
        ),
    )
    await db.execute(
        delete(models_shotgun.ShotgunTicketGenerator).where(
            models_shotgun.ShotgunTicketGenerator.session_id == session_id,
        ),
    )


async def get_paid_session_purchases(
    db: AsyncSession,
    session_id: UUID,
) -> Sequence[models_shotgun.ShotgunPurchase]:
    result = await db.execute(
        select(models_shotgun.ShotgunPurchase).where(
            models_shotgun.ShotgunPurchase.session_id == session_id,
            models_shotgun.ShotgunPurchase.paid.is_(True),
        ),
    )
    return result.scalars().all()


async def get_generator_by_id(
    db: AsyncSession,
    generator_id: UUID,
) -> models_shotgun.ShotgunTicketGenerator | None:
    result = await db.execute(
        select(models_shotgun.ShotgunTicketGenerator).where(
            models_shotgun.ShotgunTicketGenerator.id == generator_id,
        ),
    )
    return result.scalars().first()


def create_generator(
    db: AsyncSession,
    generator: models_shotgun.ShotgunTicketGenerator,
):
    db.add(generator)


async def delete_generator(db: AsyncSession, generator_id: UUID):
    """Delete a generator with its tickets"""
    await db.execute(
        delete(models_shotgun.ShotgunTicket).where(
            models_shotgun.ShotgunTicket.generator_id == generator_id,
        ),
    )
    await db.execute(
        delete(models_shotgun.ShotgunTicketGenerator).where(
            models_shotgun.ShotgunTicketGenerator.id == generator_id,
        ),
    )


async def get_session_by_id_for_purchase(
    db: AsyncSession,
    session_id: UUID,
) -> models_shotgun.ShotgunSession | None:
    await db.execute(
        select(models_shotgun.ShotgunSession)
        .where(
            models_shotgun.ShotgunSession.id == session_id,
        )
        .with_for_update(),
    )
    result_outdated_purchases = await db.execute(
        delete(models_shotgun.ShotgunPurchase).where(
            models_shotgun.ShotgunPurchase.session_id == session_id,
            models_shotgun.ShotgunPurchase.paid.is_(False),
            models_shotgun.ShotgunPurchase.purchased_on + timedelta(minutes=16)
            > datetime.now(UTC),
        ),
    )
    await db.execute(
        update(models_shotgun.ShotgunSession)
        .where(models_shotgun.ShotgunSession.id == session_id)
        .values(
            quantity=models_shotgun.ShotgunSession.quantity
            + result_outdated_purchases.rowcount,
        ),
    )
    await db.commit()
    result = await db.execute(
        select(models_shotgun.ShotgunSession)
        .where(
            models_shotgun.ShotgunSession.id == session_id,
        )
        .with_for_update(),
    )
    return result.scalars().first()


async def remove_one_place_from_session(
    db: AsyncSession,
    session_id: UUID,
):
    await db.execute(
        update(models_shotgun.ShotgunSession)
        .where(models_shotgun.ShotgunSession.id == session_id)
        .values(quantity=models_shotgun.ShotgunSession.quantity - 1),
    )


def create_purchase(db: AsyncSession, purchase: models_shotgun.ShotgunPurchase):
    db.add(purchase)


def create_ticket(db: AsyncSession, ticket: models_shotgun.ShotgunTicket):
    db.add(ticket)
