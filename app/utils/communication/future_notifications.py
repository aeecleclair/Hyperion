from datetime import datetime

from fastapi import BackgroundTasks, Depends
from app.core.notification.notification_types import CustomTopic
from app.core.notification.schemas_notification import Message
from app.dependencies import get_scheduler
from app.types.scheduler import Scheduler
from app.utils.communication.notifications import NotificationManager, NotificationTool
from sqlalchemy.ext.asyncio import AsyncSession


class FutureNotificationTool(NotificationTool):
    def __init__(
        self,
        background_tasks: BackgroundTasks,
        notification_manager: NotificationManager,
        db: AsyncSession,
        ):
        super().__init__(background_tasks, notification_manager, db)
    async def send_future_notification_to_user(
        self,
        user_id: str,
        message: Message,
        defer_date: datetime,
        job_id: str,
        scheduler: Scheduler = Depends(get_scheduler),
    ) -> None:
        
        await scheduler.queue_job_defer_to(self.send_notification_to_users,
            user_ids=[user_id],
            message=message, job_id=job_id, defer_date=defer_date)
    
    async def send_future_notification_to_topic(
        self,
        message: Message,
        custom_topic: CustomTopic,
        defer_date: datetime,
        job_id: str,
        scheduler: Scheduler = Depends(get_scheduler),
    ) -> None:
        
        await scheduler.queue_job_defer_to(self.send_notification_to_topic,
            custom_topic=custom_topic,
            message=message, job_id=job_id, defer_date=defer_date)