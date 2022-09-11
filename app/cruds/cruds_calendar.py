from datetime import datetime

from icalendar import Calendar, Event, vText
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import models_calendar

calendar_file_path = "data/ics/ae_calendar.ics"


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
        try:
            await create_icalendar_file(db, calendar_file_path)
            return event
        except Exception as error:
            await db.rollback()
            raise ValueError(error)

    except IntegrityError as error:
        await db.rollback()
        raise ValueError(error)


async def delete_event(db: AsyncSession, event_id: str) -> None:
    await db.execute(
        delete(models_calendar.Event).where(models_calendar.Event.id == event_id)
    )
    try:
        await db.commit()
        try:
            await create_icalendar_file(db, calendar_file_path)
        except Exception as error:
            await db.rollback()
            raise ValueError(error)
    except IntegrityError:
        await db.rollback()
        raise ValueError()


async def create_icalendar_file(db: AsyncSession, calendar_file_path) -> None:
    events = await get_all_events(db)

    calendar = Calendar()
    calendar.add("version", "2.0")  # Required field
    calendar.add("proid", "myecl.fr")  # Required field

    for event in events:
        ical_event = Event()
        ical_event["uid"] = f"{event.id}@myecl.fr"
        ical_event.add("summary", event.name)
        ical_event.add("description", event.description)
        ical_event.add("dtstart", event.start)
        ical_event.add("dtend", event.end)
        ical_event.add("dtstamp", datetime.now())
        ical_event.add("class", "public")
        ical_event["organizer"] = vText(event.organizer)
        ical_event["location"] = vText(event.place)

        calendar.add_component(ical_event)

    with open(calendar_file_path, "wb") as calendar_file:
        calendar_file.write(calendar.to_ical())
