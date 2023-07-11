import logging

import firebase_admin
from firebase_admin import credentials, messaging
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.cruds.cruds_notification import (
    create_message,
    get_firebase_devices_by_user_id,
    get_topic_membership_by_topic,
)
from app.models import models_notification
from app.schemas.schemas_notification import Message
from app.utils.types.notification_types import Topic

hyperion_error_logger = logging.getLogger("hyperion.error")


class NotificationManager:
    def __init__(self, settings: Settings, db: AsyncSession):
        self.use_firebase = settings.USE_FIREBASE
        self.db = db

        if self.use_firebase:
            try:
                firebase_cred = credentials.Certificate("firebase.json")
                firebase_app = firebase_admin.initialize_app(firebase_cred)
            except Exception as error:
                hyperion_error_logger.error(
                    f"Firebase is not configured correctly, disabling the notification manager. Please check a valid firebase.json file exist at the root of the project ({error})."
                )
                self.use_firebase = False

    def _send_firebase_push_notification_by_tokens(
        self, title: str | None = None, body: str | None = None, tokens: list[str] = []
    ):
        """
        Send a firebase push notification to a list of tokens.

        NOTE: we don't use this function in Hyperion, since we only use "trigger" notifications.
        """
        message = messaging.MulticastMessage(
            notification=messaging.Notification(title=title, body=body), tokens=tokens
        )
        messaging.send_multicast(message)

    def _send_firebase_trigger_notification_by_tokens(self, tokens: list[str] = []):
        """
        Send a firebase trigger notification to a list of tokens.

        Allows to let the application know that a new notification is available, without sending the content of the notification.
        """
        self._send_firebase_push_notification_by_tokens(title="trigger", tokens=tokens)

    def _send_firebase_push_notification_by_topic(
        self, topic: Topic, title: str | None = None, body: str | None = None
    ):
        """
        Send a firebase push notification for a given topic.

        NOTE: we don't use this function in Hyperion, since we only use "trigger" notifications.
        """
        message = messaging.Message(
            notification=messaging.Notification(title=title, body=body), topic=topic
        )
        messaging.send(message)

    def _send_firebase_trigger_notification_by_topic(self, topic: Topic):
        """
        Send a firebase trigger notification for a given topic.

        Allows to let the application know that a new notification is available, without sending the content of the notification.
        """
        self._send_firebase_push_notification_by_topic(title="trigger", topic=topic)

    def _subscribe_tokens_to_topic(self, topic: Topic, tokens: list[str]):
        """
        Subscribe a list of tokens to a given topic.
        """
        response = messaging.subscribe_to_topic(tokens, topic)
        if response.failure_count > 0:
            print(
                f"Failed to subscribe to topic {topic} due to {list(map(lambda e: e.reason,response.errors))}"
            )

    def _unsubscribe_tokens_to_topic(self, topic: Topic, tokens: list[str]):
        """
        Unsubscribe a list of tokens to a given topic.
        """
        response = messaging.unsubscribe_from_topic(tokens, topic)
        if response.failure_count > 0:
            print(
                f"Failed to subscribe to topic {topic} due to {list(map(lambda e: e.reason,response.errors))}"
            )

    async def add_message_for_user_in_database(
        self, message: Message, device: models_notification.FirebaseDevice
    ) -> None:
        message_model = models_notification.Message(
            firebase_device_token=device.firebase_device_token,
            **message.dict(),
        )

        try:
            await create_message(message=message_model, db=self.db)
        except Exception as error:
            hyperion_error_logger.warning(
                f"Notification: Unable to add message for device {device.firebase_device_token} to database: {error}"
            )

    async def send_notification_to_user(self, user_id: str, message: Message) -> None:
        """
        Send a notification to a user.
        This utils will find all devices related to the user and send a firebase "trigger" notification to each of them.
        This notification will prompte Titan to query the API to get the notification content.

        The "trigger" notification will only be send if firebase is correctly configured.
        """
        if not self.use_firebase:
            return

        # Get all firebase_device_token related to the user
        firebase_devices = await get_firebase_devices_by_user_id(
            user_id=user_id, db=self.db
        )

        firebase_device_tokens = []
        for device in firebase_devices:
            await self.add_message_for_user_in_database(message=message, device=device)
            firebase_device_tokens.append(device.firebase_device_token)

        try:
            self._send_firebase_trigger_notification_by_tokens(
                tokens=firebase_device_tokens
            )
        except Exception as error:
            hyperion_error_logger.warning(
                f"Notification: Unable to send firebase notification to user {user_id} with device {device.firebase_device_token}: {error}"
            )

    async def send_notification_to_topic(self, topic: Topic, message: Message) -> None:
        """
        Send a notification for a given topic.
        This utils will find all users devices subscribed to the topic and send a firebase "trigger" notification for the topic.
        This notification will prompte Titan to query the API to get the notification content.

        The "trigger" notification will only be send if firebase is correctly configured.
        """
        if not self.use_firebase:
            return

        # Get all firebase_device_token related to the user
        topic_memberships = await get_topic_membership_by_topic(
            topic=topic,
            db=self.db,
        )

        for membership in topic_memberships:
            firebase_devices = await get_firebase_devices_by_user_id(
                user_id=membership.user_id, db=self.db
            )

            for device in firebase_devices:
                await self.add_message_for_user_in_database(
                    message=message, device=device
                )

        try:
            self._send_firebase_trigger_notification_by_topic(topic=topic)
        except Exception as error:
            hyperion_error_logger.warning(
                f"Notification: Unable to send firebase notification for topic {topic}: {error}"
            )
