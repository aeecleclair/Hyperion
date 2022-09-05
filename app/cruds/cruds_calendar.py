from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import models_calendar


async def get_all_events(db: AsyncSession) -> list[models_calendar.Event]:

    # On récupère tous les éléments Event dont le user_id correspond à celui que l'on recherche
    result = await db.execute(select(models_calendar.Event))
    return result.scalars().all()


async def add_event(
    db: AsyncSession, event: models_calendar.Event
) -> models_calendar.Event:

    db.add(event)
    try:
        await db.commit()
        return event
    except IntegrityError as error:
        await db.rollback()
        raise ValueError(error)
