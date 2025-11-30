from sqlalchemy.ext.asyncio import AsyncSession

from app.core.users import cruds_users
from app.types.module_user_deleter import ModuleUserDeleter
from app.utils.tools import delete_file_from_data


class UsersUserDeleter(ModuleUserDeleter):
    async def can_delete_user(
        self,
        user_id: str,
        db: AsyncSession,
    ) -> str:
        return ""

    async def delete_user(self, user_id: str, db: AsyncSession) -> None:
        await cruds_users.delete_email_migration_code_by_user_id(
            db=db,
            user_id=user_id,
        )
        await cruds_users.delete_recover_request_by_user_id(
            db=db,
            user_id=user_id,
        )
        await cruds_users.deactivate_user(
            db=db,
            user_id=user_id,
        )
        delete_file_from_data(
            directory="profile-pictures",
            filename=user_id,
        )
