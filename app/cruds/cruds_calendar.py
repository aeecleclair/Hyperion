from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import models_calendar


async def get_all_events(db: AsyncSession) -> list[models_calendar.Event]:
    """Retriveve all the events in the database."""
    result = await db.execute(select(models_calendar.Event))
    return result.scalars().all()


async def get_event(db: AsyncSession, event_id: str) -> models_calendar.Event | None:
    """Retrieve the event corresponding to `event_id` from the database."""
    result = await db.execute(
        select(models_calendar.Event).where(models_calendar.Event.id == event_id)
    )
    return result.scalars().first()


async def add_event(
    db: AsyncSession, event: models_calendar.Event
) -> models_calendar.Event:
    """Add an event to the database."""

    db.add(event)
    try:
        await db.commit()
        return event
    except IntegrityError as error:
        await db.rollback()
        raise ValueError(error)
