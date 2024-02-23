from datetime import datetime
from typing import Sequence

from icalendar import Calendar, Event, vRecur
from pytz import timezone
from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import Settings
from app.modules.calendar import models_calendar, schemas_calendar
from app.modules.calendar.types_calendar import Decision

calendar_file_path = "data/ics/ae_calendar.ics"


async def get_all_events(db: AsyncSession) -> Sequence[models_calendar.Event]:
    """Retriveve all the events in the database."""
    result = await db.execute(
        select(models_calendar.Event).options(
            selectinload(models_calendar.Event.applicant)
        )
    )
    return result.scalars().all()


async def get_confirmed_events(
    db: AsyncSession,
) -> Sequence[models_calendar.Event]:
    result = await db.execute(
        select(models_calendar.Event).where(
            models_calendar.Event.decision == Decision.approved
        )
    )
    return result.scalars().all()


async def get_event(db: AsyncSession, event_id: str) -> models_calendar.Event | None:
    """Retrieve the event corresponding to `event_id` from the database."""
    result = await db.execute(
        select(models_calendar.Event)
        .where(models_calendar.Event.id == event_id)
        .options(selectinload(models_calendar.Event.applicant))
    )
    return result.scalars().first()


async def get_applicant_events(
    db: AsyncSession, applicant_id: str
) -> Sequence[models_calendar.Event]:
    result = await db.execute(
        select(models_calendar.Event)
        .where(models_calendar.Event.applicant_id == applicant_id)
        .options(selectinload(models_calendar.Event.applicant))
    )
    return result.scalars().all()


async def add_event(
    db: AsyncSession, event: models_calendar.Event, settings: Settings
) -> models_calendar.Event:
    """Add an event to the database."""

    db.add(event)
    try:
        await db.commit()
        return event

    except IntegrityError as error:
        await db.rollback()
        raise ValueError(error)


async def edit_event(
    db: AsyncSession, event_id: str, event: schemas_calendar.EventEdit
):
    await db.execute(
        update(models_calendar.Event)
        .where(models_calendar.Event.id == event_id)
        .values(**event.model_dump(exclude_none=True))
    )
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise ValueError()


async def delete_event(db: AsyncSession, event_id: str, settings: Settings) -> None:
    """Delete the event given in the database."""
    await db.execute(
        delete(models_calendar.Event).where(models_calendar.Event.id == event_id)
    )
    try:
        await db.commit()
        try:
            await create_icalendar_file(db, settings)
        except Exception as error:
            await db.rollback()
            raise ValueError(error)
    except IntegrityError:
        await db.rollback()
        raise ValueError()


async def confirm_event(
    db: AsyncSession, decision: Decision, event_id: str, settings: Settings
):
    await db.execute(
        update(models_calendar.Event)
        .where(models_calendar.Event.id == event_id)
        .values(decision=decision)
    )
    try:
        await db.commit()
        if decision == Decision.approved:
            try:
                await create_icalendar_file(db, settings)
            except Exception as error:
                await db.rollback()
                raise ValueError(error)
    except IntegrityError as error:
        await db.rollback()
        raise ValueError(error)


async def create_icalendar_file(db: AsyncSession, settings: Settings) -> None:
    """Create the ics file corresponding to the database. The calendar is entirely recreated each time an event is added or deleted in the db."""
    events = await get_all_events(db)

    calendar = Calendar()
    calendar.add("version", "2.0")  # Required field
    calendar.add("proid", "myecl.fr")  # Required field

    for event in events:
        if event.decision == Decision.approved:
            ical_event = Event()
            ical_event.add("uid", f"{event.id}@myecl.fr")
            ical_event.add("summary", event.name)
            ical_event.add("description", event.description)
            ical_event.add(
                "dtstart", event.start.replace(tzinfo=timezone(settings.TIMEZONE))
            )
            ical_event.add(
                "dtend", event.end.replace(tzinfo=timezone(settings.TIMEZONE))
            )
            ical_event.add("dtstamp", datetime.now(timezone(settings.TIMEZONE)))
            ical_event.add("class", "public")
            ical_event.add("organizer", event.organizer)
            ical_event.add("location", event.location)
            if event.recurrence_rule:
                ical_event.add("rrule", vRecur.from_ical(event.recurrence_rule))

            calendar.add_component(ical_event)

    with open(calendar_file_path, "wb") as calendar_file:
        calendar_file.write(calendar.to_ical())
