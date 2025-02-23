import uuid
from datetime import datetime, timedelta, timezone

from app.core.factory_core import CoreFactory
from app.core.groups.groups_type import GroupType
from app.core.users import cruds_users
from app.modules.booking import (
    cruds_booking,
    models_booking,
    schemas_booking,
    types_booking,
)
from app.utils.factory import Factory


class BookingFactory(Factory):
    def __init__(self):
        super().__init__(
            name="Booking",
            depends_on=[],
        )

    async def create_booking(self, db):
        booking_manager_id = str(uuid.uuid4())
        room_id_1 = str(uuid.uuid4())
        await cruds_booking.create_manager(
            db=db,
            manager=models_booking.Manager(
                id=booking_manager_id,
                name="BDE",
                group_id=GroupType.BDE,
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
                applicant_id=CoreFactory.demo_user_id,
                reason="Test",
                start=datetime.now(timezone.utc),
                end=datetime.now(timezone.max) + timedelta(days=1),
                creation=datetime.now() - timedelta(days=10),
                note="",
                room_id=room_id_1,
                key=True,
                recurrence_rule=None,
                entity="Entity",
            ),
        )

    async def run(self, db):
        await self.create_booking(db)

    async def should_run(self, db):
        campaigns = await cruds_booking.get_rooms(db=db)
        return len(campaigns) == 0


factory = BookingFactory()
