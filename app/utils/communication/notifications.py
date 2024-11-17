from datetime import datetime
import logging

import firebase_admin
from fastapi import BackgroundTasks, Depends
from firebase_admin import credentials, messaging
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.notification import cruds_notification, models_notification
from app.core.notification.notification_types import CustomTopic
from app.core.notification.schemas_notification import Message

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
                data={"module":message_content.action_module},
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
            response=result,
            tokens=tokens,
            db=db,
        )

    def _send_firebase_push_notification_by_topic(
        self,
        custom_topic: CustomTopic,
        message_content: Message,
    ):
        """
        Send a firebase push notification for a given topic.
        Prefer using `self._send_firebase_trigger_notification_by_topic` to send a trigger notification.
        """

        if not self.use_firebase:
            return
        message = messaging.Message(
            topic=custom_topic.to_str(),
            notification=messaging.Notification(
                    title=message_content.title,
                    body=message_content.content,
                ),
        )
        try:
            messaging.send(message)
        except messaging.FirebaseError as error:
            hyperion_error_logger.error(
                f"Notification: Unable to send firebase notification for topic {custom_topic}: {error}",
            )
            raise

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
        custom_topic: CustomTopic,
        message: Message,
        db: AsyncSession,
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
            self._send_firebase_push_notification_by_topic(custom_topic=custom_topic, message_content=message)
        except Exception as error:
            hyperion_error_logger.warning(
                f"Notification: Unable to send firebase notification for topic {custom_topic}: {error}",
            )

    async def subscribe_user_to_topic(
        self,
        custom_topic: CustomTopic,
        user_id: str,
        db: AsyncSession,
    ) -> None:
        """
        Subscribe a user to a given topic.
        """

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
            tokens = await cruds_notification.get_firebase_tokens_by_user_ids(user_ids=[user_id], db=db)
            await self.subscribe_tokens_to_topic(custom_topic=custom_topic, tokens=tokens)
        

    async def unsubscribe_user_to_topic(
        self,
        custom_topic: CustomTopic,
        user_id: str,
        db: AsyncSession,
    ) -> None:
        """
        Unsubscribe a user to a given topic.
        """
        await cruds_notification.delete_topic_membership(
            custom_topic=custom_topic,
            user_id=user_id,
            db=db,
        )
        tokens = await cruds_notification.get_firebase_tokens_by_user_ids(user_ids=[user_id], db=db)
        await self.unsubscribe_tokens_to_topic(custom_topic=custom_topic, tokens=tokens)

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
        self.db = db

    async def send_notification_to_users(self, user_ids: list[str], message: Message):
        self.background_tasks.add_task(
            self.notification_manager.send_notification_to_users,
            user_ids=user_ids,
            message=message,
            db=self.db,
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
        custom_topic: CustomTopic,
        message: Message,
    ):
        self.background_tasks.add_task(
            self.notification_manager.send_notification_to_topic,
            custom_topic=custom_topic,
            message=message,
            db=self.db,
        )