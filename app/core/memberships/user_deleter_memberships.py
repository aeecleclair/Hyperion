from sqlalchemy.ext.asyncio import AsyncSession

from app.types.module_user_deleter import ModuleUserDeleter


class MembershipsUserDeleter(ModuleUserDeleter):
    async def has_reason_not_to_delete_user(
        self,
        user_id: str,
        db: AsyncSession,
    ) -> str:
        return ""

    async def delete_user(self, user_id: str, db: AsyncSession) -> None:
        pass  # We keep the memberships for stats and history purposes
