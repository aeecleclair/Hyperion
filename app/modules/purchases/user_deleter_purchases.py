from sqlalchemy.ext.asyncio import AsyncSession

from app.types.module_user_deleter import ModuleUserDeleter


class PurchasesUserDeleter(ModuleUserDeleter):
    async def can_delete_user(
        self,
        user_id: str,
        db: AsyncSession,
    ) -> str:
        return ""

    async def delete_user(self, user_id: str, db: AsyncSession) -> None:
        pass
