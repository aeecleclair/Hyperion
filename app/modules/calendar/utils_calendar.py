from collections.abc import Sequence
from datetime import UTC, datetime

import aiofiles
from icalendar import Calendar, Event, vRecur
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.feed.utils_feed import create_feed_news, edit_feed_news
from app.core.utils.config import Settings
from app.modules.calendar import models_calendar
from app.modules.calendar.types_calendar import Decision
from app.utils.communication.notifications import NotificationTool

root = "event"
calendar_file_path = "data/ics/ae_calendar.ics"


async def add_event_to_feed(
    event: models_calendar.Event,
    db: AsyncSession,
    notification_tool: NotificationTool,
):
    await create_feed_news(
        title=event.name,
        start=event.start,
        end=event.end,
        entity=event.association.name,
        location=event.location,
        action_start=event.ticket_url_opening,
        module=root,
        module_object_id=event.id,
        image_directory="event",
        image_id=event.id,
        require_feed_admin_approval=False,
        db=db,
        notification_tool=notification_tool,
    )


async def edit_event_feed_news(
    event: models_calendar.Event,
    db: AsyncSession,
    notification_tool: NotificationTool,
):
    await edit_feed_news(
        module=root,
        module_object_id=event.id,
        title=event.name,
        start=event.start,
        end=event.end,
        entity=event.association.name,
        location=event.location,
        action_start=event.ticket_url_opening,
        require_feed_admin_approval=False,
        db=db,
        notification_tool=notification_tool,
    )


async def create_icalendar_file(
    all_events: Sequence[models_calendar.Event],
    settings: Settings,
) -> None:
    """Create the ics file corresponding to the database. The calendar is entirely recreated each time an event is added or deleted in the db."""

    calendar = Calendar()
    calendar.add("version", "2.0")  # Required field
    calendar.add("proid", settings.school.application_domain_name)  # Required field

    for event in all_events:
        if event.decision == Decision.approved:
            if event.all_day:
                start = event.start.date()
                end = event.end.date()
            else:
                start = event.start
                end = event.end
            ical_event = Event()
            ical_event.add(
                "uid",
                f"{event.id}@{settings.school.application_domain_name}",
            )
            ical_event.add("summary", event.name)
            ical_event.add("description", event.description)
            ical_event.add("dtstart", start)
            ical_event.add("dtend", end)
            ical_event.add("dtstamp", datetime.now(UTC))
            ical_event.add("class", "public")
            ical_event.add("organizer", event.association.name)
            ical_event.add("location", event.location)
            if event.recurrence_rule:
                ical_event.add("rrule", vRecur.from_ical(event.recurrence_rule))

            calendar.add_component(ical_event)

    async with aiofiles.open(calendar_file_path, mode="wb") as calendar_file:
        await calendar_file.write(calendar.to_ical())
