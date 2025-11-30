from typing import Literal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.groups import cruds_groups
from app.types.module_user_deleter import ModuleUserDeleter


class GroupsUserDeleter(ModuleUserDeleter):
    async def can_delete_user(
        self,
        user_id: str,
        db: AsyncSession,
    ) -> Literal[True] | str:
        return True

    async def delete_user(self, user_id: str, db: AsyncSession) -> None:
        await cruds_groups.delete_membership_by_user_id(
            user_id=user_id,
            db=db,
        )
