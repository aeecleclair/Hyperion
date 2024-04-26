import logging

import firebase_admin
from fastapi import BackgroundTasks
from firebase_admin import credentials, messaging
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.notification import cruds_notification, models_notification
from app.core.notification.notification_types import CustomTopic, Message

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
        except Exception as error:
            hyperion_error_logger.error(
                f"Firebase is not configured correctly, disabling the notification manager. Please check a valid firebase.json file exist at the root of the project. {error}.",
            )
            self.use_firebase = False

    async def _manage_firebase_batch_response(
        self,
        response: messaging.BatchResponse,
        tokens: list[str],
        db: AsyncSession,
    ):
        """
        Manage the response of a firebase notification. We need to assume that tokens that failed to be send are not valid anymore and delete them from the database.
        """
        if response.failure_count > 0:
            responses = response.responses
            failed_tokens = []
            for idx, resp in enumerate(responses):
                if not resp.success:
                    # Firebase may return different errors: https://firebase.google.com/docs/reference/admin/python/firebase_admin.messaging#exceptions
                    # UnregisteredError happens when the token is not valid anymore, and should thus be removed from the database
                    # Other errors may happen, we want to log them as they may indicate a problem with the firebase configuration
                    if not isinstance(
                        resp.exception,
                        firebase_admin.messaging.UnregisteredError,
                    ):
                        hyperion_error_logger.error(
                            f"Firebase: Failed to send firebase notification to token {tokens[idx]}: {resp.exception}",
                        )
                    # The order of responses corresponds to the order of the registration tokens.
                    failed_tokens.append(tokens[idx])
            hyperion_error_logger.info(
                f"{response.failure_count} messages failed to be send, removing their tokens from the database.",
            )
            await cruds_notification.batch_delete_firebase_device_by_token(
                tokens=failed_tokens,
                db=db,
            )

    async def subscribe_tokens_to_topic(
        self,
        custom_topic: CustomTopic,
        tokens: list[str],
    ):
        """
        Subscribe a list of tokens to a given topic.
        """
        if not self.use_firebase:
            return

        response = messaging.subscribe_to_topic(tokens, custom_topic.to_str())
        if response.failure_count > 0:
            hyperion_error_logger.info(
                f"Notification: Failed to subscribe to topic {custom_topic} due to {[error.reason for error in response.errors]}",
            )

    async def unsubscribe_tokens_to_topic(
        self,
        custom_topic: CustomTopic,
        tokens: list[str],
    ):
        """
        Unsubscribe a list of tokens to a given topic.
        """
        if not self.use_firebase:
            return

        messaging.unsubscribe_from_topic(tokens, custom_topic.to_str())

    async def subscribe_user_to_topic(
        self,
        custom_topic: CustomTopic,
        user_id: str,
        db: AsyncSession,
    ) -> None:
        """
        Subscribe a list of tokens to a given topic.
        """
        # Get all firebase_device_token related to the user
        firebase_devices = await cruds_notification.get_firebase_devices_by_user_id(
            user_id=user_id,
            db=db,
        )

        firebase_device_tokens = [
            device.firebase_device_token for device in firebase_devices
        ]

        if len(firebase_device_tokens) > 0:
            # Asking firebase to subscribe with an empty list of tokens will raise an error
            await self.subscribe_tokens_to_topic(
                tokens=firebase_device_tokens,
                custom_topic=custom_topic,
            )

        existing_topic_membership = (
            await cruds_notification.get_topic_membership_by_user_id_and_custom_topic(
                custom_topic=custom_topic,
                user_id=user_id,
                db=db,
            )
        )
        # If the membership already exist we don't want to create a new one
        if not existing_topic_membership:
            topic_membership = models_notification.TopicMembership(
                user_id=user_id,
                topic=custom_topic.topic,
                topic_identifier=custom_topic.topic_identifier,
            )
            await cruds_notification.create_topic_membership(
                topic_membership=topic_membership,
                db=db,
            )

    async def unsubscribe_user_to_topic(
        self,
        custom_topic: CustomTopic,
        user_id: str,
        db: AsyncSession,
    ) -> None:
        """
        Subscribe a list of tokens to a given topic.
        """
        # Get all firebase_device_token related to the user
        firebase_devices = await cruds_notification.get_firebase_devices_by_user_id(
            user_id=user_id,
            db=db,
        )

        firebase_device_tokens = [
            device.firebase_device_token for device in firebase_devices
        ]

        if len(firebase_device_tokens) > 0:
            # Asking firebase to unsubscribe with an empty list of tokens will raise an error
            await self.unsubscribe_tokens_to_topic(
                tokens=firebase_device_tokens,
                custom_topic=custom_topic,
            )

        await cruds_notification.delete_topic_membership(
            custom_topic=custom_topic,
            user_id=user_id,
            db=db,
        )

    async def send_notification_to_user_manager(
        self,
        user_id: str,
        title: str,
        body: str,
        db: AsyncSession,
    ):
        """
        Send a notification to a user.
        """
        if not self.use_firebase:
            return

        firebase_devices = await cruds_notification.get_firebase_devices_by_user_id(
            user_id=user_id,
            db=db,
        )

        firebase_device_tokens = [
            device.firebase_device_token for device in firebase_devices
        ]

        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            token=firebase_device_tokens,
        )
        return message


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
    ):
        self.background_tasks = background_tasks
        self.notification_manager = notification_manager

    async def send_notification_to_user(self, user_id: str, message: Message):
        self.background_tasks.add_task(
            messaging.send,
            self.notification_manager.send_notification_to_user_manager(
                user_id,
                message.title,
                message.content,
                self.db,
            ),
        )

    async def send_notification_to_topic(
        self,
        topic: CustomTopic,
        message: Message,
    ):
        self.background_tasks.add_task(
            messaging.send,
            messaging.Message(
                notification=messaging.Notification(
                    title=message.title,
                    body=message.content,
                ),
                topic=topic.to_str(),
            ),
        )
