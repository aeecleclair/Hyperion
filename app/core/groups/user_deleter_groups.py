from sqlalchemy.ext.asyncio import AsyncSession

from app.core.groups import cruds_groups
from app.types.module_user_deleter import ModuleUserDeleter


class GroupsUserDeleter(ModuleUserDeleter):
    async def has_reason_not_to_delete_user(
        self,
        user_id: str,
        db: AsyncSession,
    ) -> str:
        return ""

    async def delete_user(self, user_id: str, db: AsyncSession) -> None:
        await cruds_groups.delete_membership_by_user_id(
            user_id=user_id,
            db=db,
        )
