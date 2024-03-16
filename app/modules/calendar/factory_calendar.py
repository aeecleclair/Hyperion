import uuid
from datetime import UTC, datetime, timedelta

from app.core.users import cruds_users
from app.modules.calendar import cruds_calendar, models_calendar
from app.modules.calendar.types_calendar import CalendarEventType
from app.utils.factory import Factory


async def should_run(db):
    events = await cruds_calendar.get_all_events(db)
    if len(events) == 0:
        return True
    return False


async def create_event(db):
    user = await cruds_users.get_user_by_email(db, "demo.test@myecl.fr")
    event = models_calendar.Event(
        id=str(uuid.uuid4()),
        name="Test event",
        organizer="Test organizer",
        applicant_id=user.id,
        start=datetime.now(UTC),
        end=datetime.now(UTC) + timedelta(hours=1),
        all_day=False,
        location="Test location",
        type=CalendarEventType.eventAE,
        description="Test description",
        decision="Approved",
        recurrence_rule=None,
    )
    await cruds_calendar.add_event(db, event)


factory = Factory(
    name="calendar",
    depends_on=["core"],
    sub_factories=[create_event],
    should_run=should_run,
)
