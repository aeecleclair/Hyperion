from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.raid.cruds_raid import is_user_a_participant
from app.types.module_user_deleter import ModuleUserDeleter


class RaidUserDeleter(ModuleUserDeleter):
    async def has_reason_not_to_delete_user(
        self,
        user_id: str,
        db: AsyncSession,
    ) -> str:
        if await is_user_a_participant(user_id, db) is not None:
            return "\n   - User is a participant in the current edition"
        return ""

    async def delete_user(self, user_id: str, db: AsyncSession) -> None:
        pass
