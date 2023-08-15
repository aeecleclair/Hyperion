import logging

import firebase_admin
from fastapi import BackgroundTasks
from firebase_admin import credentials, messaging
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.cruds import cruds_notification
from app.models import models_notification
from app.schemas.schemas_notification import Message
from app.utils.types.notification_types import Topic

hyperion_error_logger = logging.getLogger("hyperion.error")


"""
TODO

Enlever les tokens qui ne marchent plus : https://firebase.google.com/docs/cloud-messaging/manage-tokens
Rendre tout cela asynchrone

Faire des methodes internes et des méthodes plus publiques

"""


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
                f"Firebase is not configured correctly, disabling the notification manager. Please check a valid firebase.json file exist at the root of the project. {error}."
            )
            self.use_firebase = False

    async def _manage_firebase_batch_response(
        self, response: messaging.BatchResponse, tokens: list[str], db: AsyncSession
    ):
        """
        Manage the response of a firebase notification. We need to assume that tokens that failed to be send are not valid anymore and delete them from the database.
        """
        if response.failure_count > 0:
            responses = response.responses
            failed_tokens = []
            for idx, resp in enumerate(responses):
                if not resp.success:
                    # The order of responses corresponds to the order of the registration tokens.
                    failed_tokens.append(tokens[idx])
            hyperion_error_logger.info(
                f"{response.failure_count} messages failed to be send, removing their tokens from the database."
            )
            await cruds_notification.batch_delete_firebase_device_by_token(
                tokens=tokens, db=db
            )

    async def _send_firebase_push_notification_by_tokens(
        self,
        db: AsyncSession,
        data: dict[str, str] | None = None,
        tokens: list[str] = [],
    ):
        """
        Send a firebase push notification to a list of tokens.

        We don't use this function in Hyperion, since we only use "trigger" notifications.
        """
        # See https://firebase.google.com/docs/cloud-messaging/send-message?hl=fr#send-messages-to-multiple-devices

        if not self.use_firebase:
            return

        # We can only send 500 tokens at a time
        if len(tokens) > 500:
            await self._send_firebase_push_notification_by_tokens(
                data=data, tokens=tokens[500:], db=db
            )
            tokens = tokens[:500]

        # We may pass a notification object along the data
        try:
            message = messaging.MulticastMessage(data=data, tokens=tokens)
            result = messaging.send_multicast(message)
        except messaging.FirebaseError as error:
            hyperion_error_logger.error(
                f"Notification: Unable to send firebase notification to tokens: {error}"
            )
            raise

        await self._manage_firebase_batch_response(
            response=result, tokens=tokens, db=db
        )

    async def _send_firebase_trigger_notification_by_tokens(
        self, db: AsyncSession, tokens: list[str] = []
    ):
        """
        Send a firebase trigger notification to a list of tokens. This consist to send a notification without any content.
        Allows to let the application know that a new notification is available, without sending the content of the notification.
        """

        await self._send_firebase_push_notification_by_tokens(tokens=tokens, db=db)

    def _send_firebase_push_notification_by_topic(
        self,
        topic: Topic,
        data: dict[str, str] | None = None,
    ):
        """
        Send a firebase push notification for a given topic.

        We don't use this function in Hyperion, since we only use "trigger" notifications.
        """

        if not self.use_firebase:
            return

        message = messaging.Message(data=data, topic=topic)
        try:
            messaging.send(message)
        except messaging.FirebaseError as error:
            hyperion_error_logger.error(
                f"Notification: Unable to send firebase notification for topic {topic}: {error}"
            )
            raise

    def _send_firebase_trigger_notification_by_topic(self, topic: Topic):
        """
        Send a firebase trigger notification for a given topic.

        Allows to let the application know that a new notification is available, without sending the content of the notification.
        """
        self._send_firebase_push_notification_by_topic(topic=topic)

    def subscribe_tokens_to_topic(self, topic: Topic, tokens: list[str]):
        """
        Subscribe a list of tokens to a given topic.
        """
        if not self.use_firebase:
            return

        response = messaging.subscribe_to_topic(tokens, topic)
        if response.failure_count > 0:
            hyperion_error_logger.info(
                f"Notification: Failed to subscribe to topic {topic} due to {list(map(lambda e: e.reason,response.errors))}"
            )

    def unsubscribe_tokens_to_topic(self, topic: Topic, tokens: list[str]):
        """
        Unsubscribe a list of tokens to a given topic.
        """
        if not self.use_firebase:
            return

        messaging.unsubscribe_from_topic(tokens, topic)

    async def _add_message_for_user_in_database(
        self,
        message: Message,
        tokens: list[str],
        db: AsyncSession,
    ) -> None:
        message_models = []
        for token in tokens:
            message_models.append(
                models_notification.Message(
                    firebase_device_token=token,
                    **message.dict(),
                )
            )

        # We need to remove old messages with the same context and token
        # as there can only be one message per context and token
        await cruds_notification.remove_messages_by_context_and_firebase_device_tokens_list(
            context=message.context, tokens=tokens, db=db
        )

        await cruds_notification.create_batch_messages(messages=message_models, db=db)

    async def send_notification_to_user(
        self, user_id: str, message: Message, db: AsyncSession
    ) -> None:
        """
        Send a notification to a given user.
        This utils will find all devices related to the user and send a firebase "trigger" notification to each of them.
        This notification will prompte Titan to query the API to get the notification content.

        The "trigger" notification will only be send if firebase is correctly configured.
        """
        if not self.use_firebase:
            return

        # Get all firebase_device_token related to the user
        firebase_devices = await cruds_notification.get_firebase_devices_by_user_id(
            user_id=user_id, db=db
        )

        firebase_device_tokens = [
            device.firebase_device_token for device in firebase_devices
        ]

        await self._add_message_for_user_in_database(
            message=message,
            tokens=firebase_device_tokens,
            db=db,
        )

        try:
            await self._send_firebase_trigger_notification_by_tokens(
                tokens=firebase_device_tokens, db=db
            )
        except Exception as error:
            hyperion_error_logger.warning(
                f"Notification: Unable to send firebase notification to user {user_id} with device: {error}"
            )

    async def send_notification_to_topic(
        self, topic: Topic, message: Message, db: AsyncSession
    ) -> None:
        """
        Send a notification for a given topic.
        This utils will find all users devices subscribed to the topic and send a firebase "trigger" notification for the topic.
        This notification will prompte Titan to query the API to get the notification content.

        The "trigger" notification will only be send if firebase is correctly configured.
        """
        if not self.use_firebase:
            return

        # Get all firebase_device_token related to the user
        topic_memberships = await cruds_notification.get_topic_membership_by_topic(
            topic=topic,
            db=db,
        )

        firebase_tokens = []
        for membership in topic_memberships:
            firebase_devices = await cruds_notification.get_firebase_devices_by_user_id(
                user_id=membership.user_id, db=db
            )

            for device in firebase_devices:
                firebase_tokens.append(device.firebase_device_token)

        await self._add_message_for_user_in_database(
            message=message,
            tokens=firebase_tokens,
            db=db,
        )

        try:
            self._send_firebase_trigger_notification_by_topic(topic=topic)
        except Exception as error:
            hyperion_error_logger.warning(
                f"Notification: Unable to send firebase notification for topic {topic}: {error}"
            )

    async def subscribe_user_to_topic(
        self, topic: Topic, user_id: str, db: AsyncSession
    ) -> None:
        """
        Subscribe a list of tokens to a given topic.
        """
        # Get all firebase_device_token related to the user
        firebase_devices = await cruds_notification.get_firebase_devices_by_user_id(
            user_id=user_id, db=db
        )

        firebase_device_tokens = [
            device.firebase_device_token for device in firebase_devices
        ]

        self.subscribe_tokens_to_topic(tokens=firebase_device_tokens, topic=topic)

        topic_membership = models_notification.TopicMembership(
            user_id=user_id, topic=topic
        )
        await cruds_notification.create_topic_membership(
            topic_membership=topic_membership, db=db
        )

    async def unsubscribe_user_to_topic(
        self, topic: Topic, user_id: str, db: AsyncSession
    ) -> None:
        """
        Subscribe a list of tokens to a given topic.
        """
        # Get all firebase_device_token related to the user
        firebase_devices = await cruds_notification.get_firebase_devices_by_user_id(
            user_id=user_id, db=db
        )

        firebase_device_tokens = [
            device.firebase_device_token for device in firebase_devices
        ]

        self.unsubscribe_tokens_to_topic(tokens=firebase_device_tokens, topic=topic)

        await cruds_notification.delete_topic_membership(
            topic=topic, user_id=user_id, db=db
        )


class NotificationTool:
    """
    Utility class to send notifications in the background.

    This class should be instantiated before each use with a `BackgroundTasks` manager.
    The best way to do so would be to use a
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

    async def send_notification_to_user(self, user_id: str, message: Message):
        await self.notification_manager.send_notification_to_user(
            user_id=user_id,
            message=message,
            db=self.db,
        )
        # self.background_tasks.add_task(
        #     self.notification_manager.send_notification_to_user,
        #     user_id=user_id,
        #     message=message,
        #     db=self.db,
        # )

    async def send_notification_to_topic(self, topic: Topic, message: Message):
        await self.notification_manager.send_notification_to_topic(
            topic=topic,
            message=message,
            db=self.db,
        )
        # self.background_tasks.add_task(
        #     self.notification_manager.send_notification_to_topic,
        #     topic=topic,
        #     message=message,
        #     db=self.db,
        # )
