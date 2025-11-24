from collections.abc import Sequence
from datetime import UTC, date, datetime, timedelta

import aiofiles
from icalendar import Calendar, Event, vRecur
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.calendar import models_calendar, schemas_calendar
from app.modules.calendar.types_calendar import Decision

calendar_file_path = "data/ics/ae_calendar.ics"


async def get_all_events(db: AsyncSession) -> Sequence[models_calendar.Event]:
    """Retrieve all the events in the database."""
    result = await db.execute(
        select(models_calendar.Event).options(
            selectinload(models_calendar.Event.applicant),
        ),
    )
    return result.scalars().all()


async def get_confirmed_events(
    db: AsyncSession,
) -> Sequence[models_calendar.Event]:
    result = await db.execute(
        select(models_calendar.Event).where(
            models_calendar.Event.decision == Decision.approved,
        ),
    )
    return result.scalars().all()


async def get_event(db: AsyncSession, event_id: str) -> models_calendar.Event | None:
    """Retrieve the event corresponding to `event_id` from the database."""
    result = await db.execute(
        select(models_calendar.Event)
        .where(models_calendar.Event.id == event_id)
        .options(selectinload(models_calendar.Event.applicant)),
    )
    return result.scalars().first()


async def get_applicant_events(
    db: AsyncSession,
    applicant_id: str,
) -> Sequence[models_calendar.Event]:
    result = await db.execute(
        select(models_calendar.Event)
        .where(models_calendar.Event.applicant_id == applicant_id)
        .options(selectinload(models_calendar.Event.applicant)),
    )
    return result.scalars().all()


async def add_event(
    db: AsyncSession,
    event: models_calendar.Event,
) -> models_calendar.Event:
    """Add an event to the database."""

    db.add(event)
    await db.flush()
    return event


async def edit_event(
    db: AsyncSession,
    event_id: str,
    event: schemas_calendar.EventEdit,
):
    await db.execute(
        update(models_calendar.Event)
        .where(models_calendar.Event.id == event_id)
        .values(**event.model_dump(exclude_none=True)),
    )
    await db.flush()


async def delete_event(db: AsyncSession, event_id: str) -> None:
    """Delete the event given in the database."""
    await db.execute(
        delete(models_calendar.Event).where(models_calendar.Event.id == event_id),
    )
    await db.flush()
    await create_icalendar_file(db)


async def confirm_event(db: AsyncSession, decision: Decision, event_id: str):
    await db.execute(
        update(models_calendar.Event)
        .where(models_calendar.Event.id == event_id)
        .values(decision=decision),
    )
    await db.flush()
    if decision == Decision.approved:
        await create_icalendar_file(db)


def date_all_day(dt: datetime, all_day: bool) -> date:
    """
    RFC 5545 3.6.1 :
    * The DTEND name is exclusive, so we add one day on the iCalendar file.
    * The DTSTART is inclusive, but midnight in "Europe/Paris" is one day after 11PM in UTC, so we add one day as well.
    """
    return (dt + timedelta(1)).date() if all_day else dt


async def create_icalendar_file(db: AsyncSession) -> None:
    """Create the ics file corresponding to the database. The calendar is entirely recreated each time an event is added or deleted in the db."""
    events = await get_all_events(db)

    calendar = Calendar()
    calendar.add("version", "2.0")  # Required field
    calendar.add("prodid", "-//AEECL//myecl.fr//fr-FR")  # Required field

    for event in events:
        if event.decision == Decision.approved:
            ical_event = Event()
            ical_event.add("uid", f"{event.id}@myecl.fr")
            ical_event.add("summary", event.name)
            ical_event.add("description", event.description)
            ical_event.add(
                "dtstart",
                date_all_day(event.start, event.all_day),
            )
            ical_event.add(
                "dtend",
                date_all_day(event.end, event.all_day),
            )
            ical_event.add("dtstamp", datetime.now(UTC))
            ical_event.add("class", "public")
            ical_event.add("organizer", event.organizer)
            ical_event.add("location", event.location)
            if event.recurrence_rule:
                ical_event.add("rrule", vRecur.from_ical(event.recurrence_rule))

            calendar.add_component(ical_event)

    async with aiofiles.open(calendar_file_path, mode="wb") as calendar_file:
        await calendar_file.write(calendar.to_ical())
