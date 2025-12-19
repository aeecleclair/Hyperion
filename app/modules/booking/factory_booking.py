import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.groups.factory_groups import CoreGroupsFactory
from app.core.users.factory_users import CoreUsersFactory
from app.core.utils.config import Settings
from app.modules.booking import (
    cruds_booking,
    models_booking,
    schemas_booking,
    types_booking,
)
from app.types.factory import Factory


class BookingFactory(Factory):
    depends_on = [CoreUsersFactory, CoreGroupsFactory]

    @classmethod
    async def run(cls, db: AsyncSession, settings: Settings) -> None:
        booking_manager_id = str(uuid.uuid4())
        room_id_1 = str(uuid.uuid4())
        await cruds_booking.create_manager(
            db=db,
            manager=models_booking.Manager(
                id=booking_manager_id,
                name="BDE",
                group_id=CoreGroupsFactory.groups_ids[0],
                rooms=[],
            ),
        )

        await cruds_booking.create_room(
            db=db,
            room=models_booking.Room(
                id=room_id_1,
                name="Foyer",
                manager_id=booking_manager_id,
                bookings=[],
            ),
        )

        await cruds_booking.create_booking(
            db=db,
            booking=schemas_booking.BookingComplete(
                id=str(uuid.uuid4()),
                decision=types_booking.Decision.approved,
                applicant_id=CoreUsersFactory.demo_users_id[0],
                reason="Test",
                start=datetime.now(UTC),
                end=datetime.now(UTC) + timedelta(days=1),
                creation=datetime.now(UTC) - timedelta(days=10),
                note="",
                room_id=room_id_1,
                key=True,
                recurrence_rule=None,
                entity="Entity",
            ),
        )

    @classmethod
    async def should_run(cls, db: AsyncSession):
        return len(await cruds_booking.get_rooms(db=db)) == 0
