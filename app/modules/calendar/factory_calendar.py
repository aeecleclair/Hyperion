import uuid
from datetime import UTC, datetime, timedelta

from app.core.factory_core import CoreFactory
from app.core.users import cruds_users
from app.modules.calendar import cruds_calendar, models_calendar
from app.modules.calendar.types_calendar import CalendarEventType
from app.utils.factory import Factory


class CalendarFactory(Factory):
    def __init__(self):
        super().__init__(
            name="calendar",
            depends_on=[CoreFactory],
        )

    async def should_run(self, db):
        events = await cruds_calendar.get_all_events(db)
        return len(events) == 0

    async def run(self, db):
        await self.create_event(db)

    async def create_event(self, db):
        user = await cruds_users.get_user_by_email(db, "demo.test@myecl.fr")
        if user is None:
            return
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


factory = CalendarFactory()
