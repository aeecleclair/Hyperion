from datetime import datetime

from fastapi import BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.notification.notification_types import CustomTopic
from app.core.notification.schemas_notification import Message
from app.types.scheduler import Scheduler
from app.utils.communication.notifications import NotificationManager, NotificationTool


class FutureNotificationTool(NotificationTool):
    def __init__(
        self,
        background_tasks: BackgroundTasks,
        notification_manager: NotificationManager,
        scheduler: Scheduler,
        db: AsyncSession,
        ):
        super().__init__(background_tasks, notification_manager, db)
        self.scheduler = scheduler
    async def send_future_notification_to_user_defer_to(
        self,
        user_id: str,
        message: Message,
        defer_date: datetime,
        job_id: str,
    ) -> None:

        await self.scheduler.queue_job_defer_to(self.send_notification_to_users,
            user_ids=[user_id],
            message=message, job_id=job_id, defer_date=defer_date)

    async def send_future_notification_to_topic_defer_to(
        self,
        message: Message,
        custom_topic: CustomTopic,
        defer_date: datetime,
        job_id: str,
    ) -> None:

        await self.scheduler.queue_job_defer_to(self.send_notification_to_topic,
            custom_topic=custom_topic,
            message=message, job_id=job_id, defer_date=defer_date)
        
    async def send_future_notification_to_user_time_defer(
        self,
        user_id: str,
        message: Message,
        defer_seconds: float,
        job_id: str,
    ) -> None:

        await self.scheduler.queue_job_time_defer(self.send_notification_to_users,
            user_ids=[user_id],
            message=message, job_id=job_id, defer_seconds=defer_seconds)

    async def send_future_notification_to_topic_time_defer(
        self,
        message: Message,
        custom_topic: CustomTopic,
        defer_seconds: float,
        job_id: str,
    ) -> None:

        await self.scheduler.queue_job_time_defer(self.send_notification_to_topic,
            custom_topic=custom_topic,
            message=message, job_id=job_id, defer_seconds=defer_seconds)
