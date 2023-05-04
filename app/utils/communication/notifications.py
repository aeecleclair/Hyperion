import logging

import firebase_admin
from firebase_admin import credentials, messaging
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.cruds.cruds_notification import create_message, get_firebase_devices_by_user_id
from app.models import models_notification
from app.schemas.schemas_notification import Message

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
                    "Firebase is not configured correctly, disabling the notification manager. Please check a valid firebase.json file exist at the root of the project."
                )
                self.use_firebase = False

    def _send_firebase_push_notification_by_tokens(
        self, title: str | None, body: str | None, tokens: list[str]
    ):
        """
        Send a firebase push notification to a list of tokens.
        """
        message = messaging.MulticastMessage(
            notification=messaging.Notification(title=title, body=body), tokens=tokens
        )
        messaging.send_multicast(message)

    def _send_firebase_trigger_notification_by_tokens(self, tokens):
        """
        Send a firebase trigger notification to a list of tokens.
        """
        self._send_firebase_push_notification_by_tokens(title="trigger", tokens=tokens)

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
            message_model = models_notification.Message(
                firebase_device_token=device.firebase_device_token,
                **message.dict(),
            )
            firebase_device_tokens.append(device.firebase_device_token)
            try:
                await create_message(message=message_model, db=self.db)
            except Exception as error:
                hyperion_error_logger.warning(
                    f"Notification: Unable to add message for {user_id} with device {device.firebase_device_token} to database: {error}"
                )

        try:
            self._send_firebase_trigger_notification_by_tokens(tokens=firebase_devices)
        except Exception as error:
            hyperion_error_logger.warning(
                f"Notification: Unable to send firebase notification to user {user_id} with device {device.firebase_device_token}: {error}"
            )
