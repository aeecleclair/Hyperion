from typing import Literal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.notification import cruds_notification
from app.types.module_user_deleter import ModuleUserDeleter


class NotificationUserDeleter(ModuleUserDeleter):
    async def can_delete_user(
        self,
        user_id: str,
        db: AsyncSession,
    ) -> Literal[True] | str:
        return True

    async def delete_user(self, user_id: str, db: AsyncSession) -> None:
        devices = await cruds_notification.get_firebase_devices_by_user_id(
            db=db,
            user_id=user_id,
        )
        for device in devices:
            await cruds_notification.delete_message_by_firebase_device_token(
                db=db,
                device_token=device.firebase_device_token,
            )
        await cruds_notification.delete_firebase_devices_by_user_id(
            db=db,
            user_id=user_id,
        )

        await cruds_notification.delete_topic_membership_by_user_id(
            db=db,
            user_id=user_id,
        )
