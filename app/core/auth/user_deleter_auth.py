from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import cruds_auth
from app.types.module_user_deleter import ModuleUserDeleter


class AuthUserDeleter(ModuleUserDeleter):
    async def has_reason_not_to_delete_user(
        self,
        user_id: str,
        db: AsyncSession,
    ) -> str:
        return ""

    async def delete_user(self, user_id: str, db: AsyncSession) -> None:
        await cruds_auth.delete_authorization_token_by_user_id(
            db=db,
            user_id=user_id,
        )
        await cruds_auth.delete_refresh_token_by_user_id(
            db=db,
            user_id=user_id,
        )
