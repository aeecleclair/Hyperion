import logging

import firebase_admin
from fastapi import BackgroundTasks
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
                    # Firebase may return different errors: https://firebase.google.com/docs/reference/admin/python/firebase_admin.messaging#exceptions
                    # UnregisteredError happens when the token is not valid anymore, and should thus be removed from the database
                    # Other errors may happen, we want to log them as they may indicate a problem with the firebase configuration
                    if not isinstance(
                        resp.exception, firebase_admin.messaging.UnregisteredError
                    ):
                        hyperion_error_logger.error(
                            f"Firebase: Failed to send firebase notification to token {tokens[idx]}: {resp.exception}"
                        )
                    # The order of responses corresponds to the order of the registration tokens.
                    failed_tokens.append(tokens[idx])
            hyperion_error_logger.info(
                f"{response.failure_count} messages failed to be send, removing their tokens from the database."
            )
            await cruds_notification.batch_delete_firebase_device_by_token(
                tokens=failed_tokens, db=db
            )

    async def _send_firebase_push_notification_by_tokens(
        self,
        db: AsyncSession,
        tokens: list[str] = [],
    ):
        """
        Send a firebase push notification to a list of tokens.

        Prefer using `self._send_firebase_trigger_notification_by_tokens` to send a trigger notification.
        """
        # See https://firebase.google.com/docs/cloud-messaging/send-message?hl=fr#send-messages-to-multiple-devices

        if not self.use_firebase:
            return

        # We can only send 500 tokens at a time
        if len(tokens) > 500:
            await self._send_firebase_push_notification_by_tokens(
                tokens=tokens[500:], db=db
            )
            tokens = tokens[:500]

        # We may pass a notification object along the data
        try:
            # Set high priority for android, and background notification for iOS
            # This allow to ensure that the notification will be processed in the background
            # See https://firebase.google.com/docs/cloud-messaging/concept-options#setting-the-priority-of-a-message
            # And https://developer.apple.com/documentation/usernotifications/setting_up_a_remote_notification_server/pushing_background_updates_to_your_app
            androidconfig = messaging.AndroidConfig(priority="high")
            apnsconfig = messaging.APNSConfig(
                headers={"apns-priority": "5", "apns-push-type": "background"},
                payload=messaging.APNSPayload(
                    aps=messaging.Aps(content_available=True)
                ),
            )
            message = messaging.MulticastMessage(
                tokens=tokens, android=androidconfig, apns=apnsconfig
            )
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
        Send a firebase trigger notification to a list of tokens.
        This approach let the application know that a new notification is available,
        without sending the content of the notification.
        This is better for privacy and RGPD compliance.
        """

        # Push without any data or notification may not be processed by the app in the background.
        # We thus need to send a data object with a dummy key to make sure the notification is processed.
        # See https://stackoverflow.com/questions/59298850/firebase-messaging-background-message-handler-method-not-called-when-the-app
        await self._send_firebase_push_notification_by_tokens(tokens=tokens, db=db)

    def _send_firebase_push_notification_by_topic(
        self,
        custom_topic: CustomTopic,
    ):
        """
        Send a firebase push notification for a given topic.

        Prefer using `self._send_firebase_trigger_notification_by_topic` to send a trigger notification.
        """

        if not self.use_firebase:
            return

        # Set high priority for android, and background notification for iOS
        # This allow to ensure that the notification will be processed in the background
        # See https://firebase.google.com/docs/cloud-messaging/concept-options#setting-the-priority-of-a-message
        # And https://developer.apple.com/documentation/usernotifications/setting_up_a_remote_notification_server/pushing_background_updates_to_your_app
        androidconfig = messaging.AndroidConfig(priority="high")
        apnsconfig = messaging.APNSConfig(
            headers={"apns-priority": "5", "apns-push-type": "background"},
            payload=messaging.APNSPayload(aps=messaging.Aps(content_available=True)),
        )
        message = messaging.Message(
            topic=custom_topic.to_str(),
            android=androidconfig,
            apns=apnsconfig,
        )
        try:
            messaging.send(message)
        except messaging.FirebaseError as error:
            hyperion_error_logger.error(
                f"Notification: Unable to send firebase notification for topic {custom_topic}: {error}"
            )
            raise

    def _send_firebase_trigger_notification_by_topic(self, custom_topic: CustomTopic):
        """
        Send a firebase trigger notification for a given topic.

        Send a firebase trigger notification to a list of tokens.
        This approach let the application know that a new notification is available,
        without sending the content of the notification.
        This is better for privacy and RGPD compliance.
        """

        # Push without any data or notification may not be processed by the app in the background.
        # We thus need to send a data object with a dummy key to make sure the notification is processed.
        # See https://stackoverflow.com/questions/59298850/firebase-messaging-background-message-handler-method-not-called-when-the-app
        self._send_firebase_push_notification_by_topic(custom_topic=custom_topic)

    async def subscribe_tokens_to_topic(
        self, custom_topic: CustomTopic, tokens: list[str]
    ):
        """
        Subscribe a list of tokens to a given topic.
        """
        if not self.use_firebase:
            return

        response = messaging.subscribe_to_topic(tokens, custom_topic.to_str())
        if response.failure_count > 0:
            hyperion_error_logger.info(
                f"Notification: Failed to subscribe to topic {custom_topic} due to {list(map(lambda e: e.reason,response.errors))}"
            )

    async def unsubscribe_tokens_to_topic(
        self, custom_topic: CustomTopic, tokens: list[str]
    ):
        """
        Unsubscribe a list of tokens to a given topic.
        """
        if not self.use_firebase:
            return

        messaging.unsubscribe_from_topic(tokens, custom_topic.to_str())

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
                    **message.model_dump(),
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
        This notification will prompt Titan to query the API to get the notification content.

        The "trigger" notification will only be send if firebase is correctly configured.
        """
        if not self.use_firebase:
            hyperion_error_logger.info(
                "Firebase is disabled, not sending notification."
            )
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
        self, custom_topic: CustomTopic, message: Message, db: AsyncSession
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
        topic_memberships = await cruds_notification.get_topic_memberships_by_topic(
            custom_topic=custom_topic,
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
            self._send_firebase_trigger_notification_by_topic(custom_topic=custom_topic)
        except Exception as error:
            hyperion_error_logger.warning(
                f"Notification: Unable to send firebase notification for topic {custom_topic}: {error}"
            )

    async def subscribe_user_to_topic(
        self, custom_topic: CustomTopic, user_id: str, db: AsyncSession
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

        if len(firebase_device_tokens) > 0:
            # Asking firebase to subscribe with an empty list of tokens will raise an error
            await self.subscribe_tokens_to_topic(
                tokens=firebase_device_tokens, custom_topic=custom_topic
            )

        existing_topic_membership = (
            await cruds_notification.get_topic_membership_by_user_id_and_custom_topic(
                custom_topic=custom_topic, user_id=user_id, db=db
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
                topic_membership=topic_membership, db=db
            )

    async def unsubscribe_user_to_topic(
        self, custom_topic: CustomTopic, user_id: str, db: AsyncSession
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

        if len(firebase_device_tokens) > 0:
            # Asking firebase to unsubscribe with an empty list of tokens will raise an error
            await self.unsubscribe_tokens_to_topic(
                tokens=firebase_device_tokens, custom_topic=custom_topic
            )

        await cruds_notification.delete_topic_membership(
            custom_topic=custom_topic, user_id=user_id, db=db
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
    ):
        self.background_tasks = background_tasks
        self.notification_manager = notification_manager
        self.db = db

    async def send_notification_to_user(self, user_id: str, message: Message):
        self.background_tasks.add_task(
            self.notification_manager.send_notification_to_user,
            user_id=user_id,
            message=message,
            db=self.db,
        )

    async def send_notification_to_topic(
        self, custom_topic: CustomTopic, message: Message
    ):
        self.background_tasks.add_task(
            self.notification_manager.send_notification_to_topic,
            custom_topic=custom_topic,
            message=message,
            db=self.db,
        )
