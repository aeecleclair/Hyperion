from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.booking import cruds_booking
from app.types.module_user_deleter import ModuleUserDeleter


class BookingUserDeleter(ModuleUserDeleter):
    async def can_delete_user(
        self,
        user_id: str,
        db: AsyncSession,
    ) -> str:
        user_bookings = await cruds_booking.get_applicant_bookings(
            db=db,
            applicant_id=user_id,
        )
        reasons = [
            f"User has booking in future: {booking.id}"
            for booking in user_bookings
            if booking.end > datetime.now(tz=UTC)
        ]
        if reasons:
            return "\n   - ".join(reasons)
        return ""

    async def delete_user(self, user_id: str, db: AsyncSession) -> None:
        pass
