from typing import Literal

from sqlalchemy.ext.asyncio import AsyncSession

from app.types.module_user_deleter import ModuleUserDeleter


class SchoolsUserDeleter(ModuleUserDeleter):
    async def can_delete_user(
        self,
        user_id: str,
        db: AsyncSession,
    ) -> Literal[True] | str:
        return True

    async def delete_user(self, user_id: str, db: AsyncSession) -> None:
        pass
