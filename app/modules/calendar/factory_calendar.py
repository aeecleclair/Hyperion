import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.users.factory_users import CoreUsersFactory
from app.modules.calendar import cruds_calendar, models_calendar
from app.modules.calendar.types_calendar import CalendarEventType
from app.types.factory import Factory


class CalendarFactory(Factory):
    def __init__(self):
        super().__init__(
            depends_on=[CoreUsersFactory],
        )

    async def run(self, db: AsyncSession):
        event = models_calendar.Event(
            id=str(uuid.uuid4()),
            name="Test event",
            organizer="Test organizer",
            applicant_id=CoreUsersFactory.demo_users_id[0],
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

    async def should_run(self, db: AsyncSession):
        return len(await cruds_calendar.get_all_events(db)) == 0
