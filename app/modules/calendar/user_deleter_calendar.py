from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.calendar import cruds_calendar
from app.types.module_user_deleter import ModuleUserDeleter


class CalendarUserDeleter(ModuleUserDeleter):
    async def can_delete_user(
        self,
        user_id: str,
        db: AsyncSession,
    ) -> str:
        user_events = await cruds_calendar.get_applicant_events(
            db=db,
            applicant_id=user_id,
        )
        reasons = [
            f"User has booking in future: {event.id}"
            for event in user_events
            if event.end > datetime.now(tz=UTC)
        ]
        if reasons:
            return "\n   - ".join(reasons)
        return ""

    async def delete_user(self, user_id: str, db: AsyncSession) -> None:
        pass
