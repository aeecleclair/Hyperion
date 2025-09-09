import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.associations.factory_associations import AssociationsFactory
from app.core.users.factory_users import CoreUsersFactory
from app.core.utils.config import Settings
from app.modules.calendar import cruds_calendar, models_calendar
from app.modules.calendar.types_calendar import Decision
from app.types.factory import Factory


class CalendarFactory(Factory):
    depends_on = [CoreUsersFactory, AssociationsFactory]

    @classmethod
    async def run(cls, db: AsyncSession, settings: Settings) -> None:
        event = models_calendar.Event(
            id=uuid.uuid4(),
            name="Test event",
            association_id=AssociationsFactory.association_ids[0],
            applicant_id=CoreUsersFactory.demo_users_id[0],
            start=datetime.now(UTC),
            end=datetime.now(UTC) + timedelta(hours=1),
            all_day=False,
            location="Test location",
            description="Test description",
            decision=Decision.approved,
            recurrence_rule=None,
            ticket_url_opening=None,
            ticket_url=None,
            notification=False,
        )
        await cruds_calendar.add_event(db, event)

        day_long_event = models_calendar.Event(
            id=uuid.uuid4(),
            name="Test day long event",
            association_id=AssociationsFactory.association_ids[0],
            applicant_id=CoreUsersFactory.demo_users_id[0],
            start=datetime.now(UTC),
            end=datetime.now(UTC) + timedelta(days=3),
            all_day=True,
            location="Test location",
            description="Test description",
            decision=Decision.approved,
            recurrence_rule=None,
            ticket_url_opening=None,
            ticket_url=None,
            notification=False,
        )
        await cruds_calendar.add_event(db, day_long_event)

    @classmethod
    async def should_run(cls, db: AsyncSession):
        return len(await cruds_calendar.get_all_events(db)) == 0
