import logging
from datetime import datetime
from uuid import UUID

import firebase_admin
from fastapi import BackgroundTasks
from firebase_admin import credentials, messaging
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.notification import cruds_notification, models_notification
from app.core.notification.schemas_notification import Message
from app.core.users import cruds_users
from app.core.utils.config import Settings
from app.types.scheduler import Scheduler

hyperion_error_logger = logging.getLogger("hyperion.error")


class NotificationManager:
    """
    Notification manager for Firebase.
    This class should only be instantiated once.
    """

    # See https://firebase.google.com/docs/cloud-messaging/send-message?hl=fr for documentation and examples

    def __init__(self, settings: Settings):
        self.use_firebase = settings.USE_FIREBASE

        if not self.use_firebase:
            hyperion_error_logger.info("Firebase is configured to be disabled.")
            return

        try:
            firebase_cred = credentials.Certificate("firebase.json")
            firebase_admin.initialize_app(firebase_cred)
        except Exception:
            hyperion_error_logger.exception(
                "Firebase is not configured correctly, disabling the notification manager. Please check a valid firebase.json file exist at the root of the project.",
            )
            self.use_firebase = False

    async def _manage_firebase_batch_response(
        self,
        message_content: Message,
        response: messaging.BatchResponse,
        tokens: list[str],
        db: AsyncSession,
    ):
        """
        Manage the response of a firebase notification. We need to assume that tokens that failed to be send are not valid anymore and delete them from the database.
        """
        if response.failure_count > 0:
            responses: list[messaging.SendResponse] = response.responses
            failed_tokens: list[str] = []
            mismatching_tokens: list[str] = []
            for idx, resp in enumerate(responses):
                if not resp.success:
                    # Firebase may return different errors: https://firebase.google.com/docs/reference/admin/python/firebase_admin.messaging#exceptions
                    # UnregisteredError happens when the token is not valid anymore, and should thus be removed from the database
                    # Other errors may happen, we want to log them as they may indicate a problem with the firebase configuration
                    if not isinstance(
                        resp.exception,
                        messaging.UnregisteredError,
                    ):
                        if isinstance(
                            resp.exception,
                            messaging.SenderIdMismatchError,
                        ):
                            mismatching_tokens.append(tokens[idx])
                        else:
                            hyperion_error_logger.error(
                                f"Firebase: Failed to send firebase notification to token {tokens[idx]}: {resp.exception}",
                            )
                    # The order of responses corresponds to the order of the registration tokens.
                    failed_tokens.append(tokens[idx])
            hyperion_error_logger.error(
                # chr(10) == "\n"
                f"""
                    Firebase: SenderId mismatch for users:
                    {chr(10).join(await cruds_notification.get_user_ids_by_firebase_tokens(tokens=mismatching_tokens, db=db))}
                """,
            )
            # TODO: ask to register the device again and retry sending, using the message_content arg
            hyperion_error_logger.info(
                f"{response.failure_count} messages failed to be send, removing their tokens from the database.",
            )
            await cruds_notification.batch_delete_firebase_device_by_token(
                tokens=failed_tokens,
                db=db,
            )

    async def _send_firebase_push_notification_by_tokens(
        self,
        db: AsyncSession,
        tokens: list[str],
        message_content: Message,
    ):
        """
        Send a firebase push notification to a list of tokens.

        Prefer using `self._send_firebase_trigger_notification_by_tokens` to send a trigger notification.
        """
        # See https://firebase.google.com/docs/cloud-messaging/send-message?hl=fr#send-messages-to-multiple-devices
        if not self.use_firebase:
            return

        if len(tokens) == 0:
            # We should not try to send a message to an emtpy list of tokens
            # or we will get an error "max_workers must be greater than 0"
            # See https://github.com/firebase/firebase-admin-python/issues/792
            return

        # We can only send 500 tokens at a time
        if len(tokens) > 500:
            await self._send_firebase_push_notification_by_tokens(
                tokens=tokens[500:],
                db=db,
                message_content=message_content,
            )
            tokens = tokens[:500]

        try:
            message = messaging.MulticastMessage(
                tokens=tokens,
                data={"action_module": message_content.action_module},
                notification=messaging.Notification(
                    title=message_content.title,
                    body=message_content.content,
                ),
            )

            result = messaging.send_each_for_multicast(message)
        except Exception:
            hyperion_error_logger.exception(
                "Notification: Unable to send firebase notification to tokens",
            )
            raise
        await self._manage_firebase_batch_response(
            message_content,
            response=result,
            tokens=tokens,
            db=db,
        )

    def _send_firebase_push_notification_by_topic(
        self,
        topic_id: UUID,
        message_content: Message,
    ):
        """
        Send a firebase push notification for a given topic.
        Prefer using `self._send_firebase_trigger_notification_by_topic` to send a trigger notification.
        """

        if not self.use_firebase:
            return

        topic = str(topic_id)
        message = messaging.Message(
            topic=topic,
            notification=messaging.Notification(
                title=message_content.title,
                body=message_content.content,
            ),
        )
        try:
            messaging.send(message)
        except messaging.FirebaseError:
            hyperion_error_logger.exception(
                f"Notification: Unable to send firebase notification for topic {topic}",
            )
            raise

    async def subscribe_tokens_to_topic(
        self,
        topic_id: UUID,
        tokens: list[str],
    ):
        """
        Subscribe a list of tokens to a given topic.
        """
        if not self.use_firebase:
            return

        if len(tokens) == 0:
            return

        topic = str(topic_id)
        response = messaging.subscribe_to_topic(tokens, topic)
        if response.failure_count > 0:
            hyperion_error_logger.info(
                f"Notification: Failed to subscribe to topic {topic} due to {[error.reason for error in response.errors]}",
            )

    async def unsubscribe_tokens_to_topic(
        self,
        topic_id: UUID,
        tokens: list[str],
    ):
        """
        Unsubscribe a list of tokens to a given topic.
        """
        if not self.use_firebase:
            return

        topic = str(topic_id)
        messaging.unsubscribe_from_topic(tokens, topic)

    async def send_notification_to_users(
        self,
        user_ids: list[str],
        message: Message,
        db: AsyncSession,
    ) -> None:
        """
        Send a notification to a given user.
        This utils will find all devices related to the user and send a firebase "trigger" notification to each of them.
        This notification will prompt Titan to query the API to get the notification content.

        The "trigger" notification will only be send if firebase is correctly configured.
        """
        if not self.use_firebase:
            hyperion_error_logger.info(
                "Firebase is disabled, not sending notification.",
            )
            return

        # Get all firebase_device_token related to the user
        firebase_device_tokens = (
            await cruds_notification.get_firebase_tokens_by_user_ids(
                user_ids=user_ids,
                db=db,
            )
        )

        try:
            await self._send_firebase_push_notification_by_tokens(
                tokens=firebase_device_tokens,
                db=db,
                message_content=message,
            )
        except Exception as error:
            hyperion_error_logger.warning(
                f"Notification: Unable to send firebase notification to users {user_ids} with device: {error}",
            )

    async def send_notification_to_topic(
        self,
        topic_id: UUID,
        message: Message,
    ) -> None:
        """
        Send a notification to a given topic.
        This utils will find all users related to the topic and send a firebase "trigger" notification to each of them.
        This notification will prompt Titan to query the API to get the notification content.

        The "trigger" notification will only be send if firebase is correctly configured.
        """
        if not self.use_firebase:
            hyperion_error_logger.info(
                "Firebase is disabled, not sending notification.",
            )
            return

        try:
            self._send_firebase_push_notification_by_topic(
                topic_id=topic_id,
                message_content=message,
            )
        except Exception as error:
            hyperion_error_logger.warning(
                f"Notification: Unable to send firebase notification for topic {topic_id}: {error}",
            )

    async def subscribe_user_to_topic(
        self,
        topic_id: UUID,
        user_id: str,
        db: AsyncSession,
    ) -> None:
        """
        Subscribe a user to a given topic.
        """

        existing_topic_membership = (
            await cruds_notification.get_topic_membership_by_user_id_and_topic_id(
                user_id=user_id,
                topic_id=topic_id,
                db=db,
            )
        )

        # If the membership already exist we don't want to create a new one
        if not existing_topic_membership:
            topic_membership = models_notification.TopicMembership(
                user_id=user_id,
                topic_id=topic_id,
            )
            await cruds_notification.create_topic_membership(
                topic_membership=topic_membership,
                db=db,
            )
            tokens = await cruds_notification.get_firebase_tokens_by_user_ids(
                user_ids=[user_id],
                db=db,
            )

            await self.subscribe_tokens_to_topic(
                topic_id=topic_id,
                tokens=tokens,
            )

    async def unsubscribe_user_to_topic(
        self,
        topic_id: UUID,
        user_id: str,
        db: AsyncSession,
    ) -> None:
        """
        Unsubscribe a user to a given topic.
        """
        await cruds_notification.delete_topic_membership(
            topic_id=topic_id,
            user_id=user_id,
            db=db,
        )
        tokens = await cruds_notification.get_firebase_tokens_by_user_ids(
            user_ids=[user_id],
            db=db,
        )
        await self.unsubscribe_tokens_to_topic(topic_id=topic_id, tokens=tokens)

    async def register_new_topic(
        self,
        topic_id: UUID,
        name: str,
        module_root: str,
        topic_identifier: str | None,
        restrict_to_group_id: str | None,
        restrict_to_members: bool,
        db: AsyncSession,
    ):
        await cruds_notification.create_notification_topic(
            notification_topic=models_notification.NotificationTopic(
                id=topic_id,
                name=name,
                module_root=module_root,
                topic_identifier=topic_identifier,
                restrict_to_group_id=restrict_to_group_id,
                restrict_to_members=restrict_to_members,
            ),
            db=db,
        )

        # We want, by default, to register users to this new topic
        users = await cruds_users.get_users(
            db=db,
            included_groups=[restrict_to_group_id] if restrict_to_group_id else None,
        )
        for user in users:
            await self.subscribe_user_to_topic(
                topic_id=topic_id,
                user_id=user.id,
                db=db,
            )


class NotificationTool:
    """
    Utility class to send notifications in the background.

    This class should be instantiated before each use with a `BackgroundTasks` manager.
    The best way to do so would be to use a dependency that instantiate this class
    the first time it is used and the return the same instance for each subsequent use.
    """

    def __init__(
        self,
        background_tasks: BackgroundTasks,
        notification_manager: NotificationManager,
        db: AsyncSession,
        # scheduler: Scheduler,
    ):
        self.background_tasks = background_tasks
        self.notification_manager = notification_manager
        self.db = db
        # self.scheduler = scheduler

    async def send_notification_to_group(
        self,
        group_id: str,
        message: Message,
        scheduler: Scheduler | None = None,
        defer_date: datetime | None = None,
        job_id: str | None = None,
    ):
        users = await cruds_users.get_users(
            included_groups=[group_id],
            db=self.db,
        )
        user_ids = [user.id for user in users]

        await self.send_notification_to_users(
            user_ids=user_ids,
            message=message,
            scheduler=scheduler,
            defer_date=defer_date,
            job_id=job_id,
        )

    async def send_notification_to_users(
        self,
        user_ids: list[str],
        message: Message,
        scheduler: Scheduler | None = None,
        defer_date: datetime | None = None,
        job_id: str | None = None,
    ):
        if defer_date is not None and scheduler is not None and job_id is not None:
            await self.send_future_notification_to_users_defer_to(
                user_ids=user_ids,
                message=message,
                scheduler=scheduler,
                defer_date=defer_date,
                job_id=job_id,
            )
        else:
            self.background_tasks.add_task(
                self.notification_manager.send_notification_to_users,
                user_ids=user_ids,
                message=message,
                db=self.db,
            )

    async def send_future_notification_to_users_defer_to(
        self,
        user_ids: list[str],
        message: Message,
        scheduler: Scheduler,
        defer_date: datetime,
        job_id: str,
    ):
        await scheduler.cancel_job(job_id=job_id)
        await scheduler.queue_job_defer_to(
            self.notification_manager.send_notification_to_users,
            user_ids=user_ids,
            message=message,
            job_id=job_id,
            defer_date=defer_date,
        )

    async def send_notification_to_user(
        self,
        user_id: str,
        message: Message,
    ) -> None:
        await self.send_notification_to_users(
            user_ids=[user_id],
            message=message,
        )

    async def send_notification_to_topic(
        self,
        topic_id: UUID,
        message: Message,
        scheduler: Scheduler | None = None,
        defer_date: datetime | None = None,
        job_id: str | None = None,
    ):
        if defer_date is not None and scheduler is not None and job_id is not None:
            await self.send_future_notification_to_topic_defer_to(
                topic_id=topic_id,
                message=message,
                scheduler=scheduler,
                defer_date=defer_date,
                job_id=job_id,
            )
        else:
            self.background_tasks.add_task(
                self.notification_manager.send_notification_to_topic,
                topic_id=topic_id,
                message=message,
            )

    async def send_future_notification_to_topic_defer_to(
        self,
        topic_id: UUID,
        message: Message,
        scheduler: Scheduler,
        defer_date: datetime,
        job_id: str,
    ):
        await scheduler.cancel_job(job_id=job_id)
        await scheduler.queue_job_defer_to(
            self.notification_manager.send_notification_to_topic,
            topic_id=topic_id,
            message=message,
            job_id=job_id,
            defer_date=defer_date,
        )

    async def cancel_notification(
        self,
        scheduler: Scheduler,
        job_id: str,
    ):
        await scheduler.cancel_job(job_id=job_id)
