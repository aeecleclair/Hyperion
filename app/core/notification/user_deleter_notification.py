from sqlalchemy.ext.asyncio import AsyncSession

from app.core.notification import cruds_notification
from app.types.module_user_deleter import ModuleUserDeleter


class NotificationUserDeleter(ModuleUserDeleter):
    async def has_reason_not_to_delete_user(
        self,
        user_id: str,
        db: AsyncSession,
    ) -> str:
        return ""

    async def delete_user(self, user_id: str, db: AsyncSession) -> None:
        await cruds_notification.delete_firebase_devices_by_user_id(
            db=db,
            user_id=user_id,
        )
        await cruds_notification.delete_topic_membership_by_user_id(
            db=db,
            user_id=user_id,
        )
