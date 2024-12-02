from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Body, Depends, HTTPException, Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import models_core
from app.core.groups.groups_type import GroupType
from app.core.notification import (
    cruds_notification,
    models_notification,
    schemas_notification,
)
from app.core.notification.notification_types import CustomTopic, Topic
from app.dependencies import (
    get_db,
    get_notification_manager,
    get_notification_tool,
    is_user,
    is_user_in,
)
from app.utils.communication.notifications import NotificationManager, NotificationTool

router = APIRouter(tags=["Notifications"])


@router.post(
    "/notification/devices",
    status_code=204,
)
async def register_firebase_device(
    firebase_token: str = Body(embed=True),
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user()),
    notification_manager: NotificationManager = Depends(get_notification_manager),
):
    """
    Register a firebase device for the user, if the device already exists, this will update the creation date.
    This endpoint should be called once a month to ensure that the token is still valide.

    **The user must be authenticated to use this endpoint**
    """

    # If there is already a device with this token, we need to update the register date
    firebase_device = await cruds_notification.get_firebase_devices_by_firebase_token(
        firebase_token=firebase_token,
        db=db,
    )

    if firebase_device is not None:
        if firebase_device.user_id == user.id:
            # Update the register date
            await cruds_notification.update_firebase_devices_register_date(
                firebase_device_token=firebase_token,
                new_register_date=datetime.now(tz=UTC).date(),
                db=db,
            )
            return
        # If the user is not the same, we don't want the new user to receive the notifications of the old one
        await cruds_notification.delete_firebase_devices(
            firebase_device_token=firebase_token,
            db=db,
        )

    firebase_device = models_notification.FirebaseDevice(
        user_id=user.id,
        firebase_device_token=firebase_token,
        register_date=datetime.now(tz=UTC).date(),
    )

    await cruds_notification.create_firebase_devices(
        firebase_device=firebase_device,
        db=db,
    )


@router.delete(
    "/notification/devices/{firebase_token}",
    status_code=204,
)
async def unregister_firebase_device(
    firebase_token: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user()),
    notification_manager: NotificationManager = Depends(get_notification_manager),
):
    """
    Unregister a new firebase device for the user

    **The user must be authenticated to use this endpoint**
    """
    # Anybody may unregister a device if they know its token, which should be secret

    await cruds_notification.delete_firebase_devices(
        firebase_device_token=firebase_token,
        db=db,
    )


@router.get(
    "/notification/messages/{firebase_token}",
    response_model=list[schemas_notification.Message],
    status_code=200,
)
async def get_messages(
    firebase_token: str,
    db: AsyncSession = Depends(get_db),
    # If we want to enable authentification for /messages/{firebase_token} endpoint, we may to uncomment the following line
    # user: models_core.CoreUser = Depends(is_user()),
):
    """
    Get all messages for a specific device from the user

    **The user must be authenticated to use this endpoint**
    """
    firebase_device = await cruds_notification.get_firebase_devices_by_user_id_and_firebase_token(
        # If we want to enable authentification for /messages/{firebase_token} endpoint, we may to uncomment the following line
        firebase_token=firebase_token,
        db=db,  # user_id=user.id,
    )

    if firebase_device is None:
        raise HTTPException(
            status_code=404,
            detail="Device not found for user",  # {user.id}"
        )

    messages = await cruds_notification.get_messages_by_firebase_token(
        firebase_token=firebase_token,
        db=db,
    )

    await cruds_notification.remove_message_by_firebase_device_token(
        firebase_device_token=firebase_token,
        db=db,
    )

    return messages


@router.post(
    "/notification/topics/{topic_str}/subscribe",
    status_code=204,
)
async def subscribe_to_topic(
    topic_str: str = Path(
        description="The topic to subscribe to. The Topic may be followed by an additional identifier (ex: cinema_4c029b5f-2bf7-4b70-85d4-340a4bd28653)",
    ),
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user()),
    notification_manager: NotificationManager = Depends(get_notification_manager),
):
    """
    Subscribe to a topic

    **The user must be authenticated to use this endpoint**
    """

    try:
        custom_topic = CustomTopic.from_str(topic_str)
    except Exception as error:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid custom topic: {error}",
        )

    await notification_manager.subscribe_user_to_topic(
        user_id=user.id,
        custom_topic=custom_topic,
        db=db,
    )


@router.post(
    "/notification/topics/{topic_str}/unsubscribe",
    status_code=204,
)
async def unsubscribe_to_topic(
    topic_str: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user()),
    notification_manager: NotificationManager = Depends(get_notification_manager),
):
    """
    Unsubscribe to a topic

    **The user must be authenticated to use this endpoint**
    """

    custom_topic = CustomTopic.from_str(topic_str)

    await notification_manager.unsubscribe_user_to_topic(
        user_id=user.id,
        custom_topic=custom_topic,
        db=db,
    )


@router.get(
    "/notification/topics",
    status_code=200,
    response_model=list[str],
)
async def get_topic(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user()),
):
    """
    Get topics the user is subscribed to
    Does not return session topics (those with a topic_identifier)

    **The user must be authenticated to use this endpoint**
    """

    memberships = await cruds_notification.get_topic_memberships_by_user_id(
        user_id=user.id,
        db=db,
    )

    return [
        CustomTopic(topic=membership.topic).to_str()
        for membership in memberships
        if not membership.topic_identifier
    ]


@router.get(
    "/notification/topics/{topic}",
    status_code=200,
    response_model=list[str],
)
async def get_topic_identifier(
    topic: Topic,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user()),
):
    """
    Get custom topic (with identifiers) the user is subscribed to

    **The user must be authenticated to use this endpoint**
    """

    memberships = await cruds_notification.get_topic_memberships_with_identifiers_by_user_id_and_topic(
        user_id=user.id,
        db=db,
        topic=topic,
    )

    return [
        CustomTopic(
            topic=membership.topic,
            topic_identifier=membership.topic_identifier,
        ).to_str()
        for membership in memberships
    ]


@router.post(
    "/notification/send",
    status_code=201,
)
async def send_notification(
    user: models_core.CoreUser = Depends(is_user_in(GroupType.admin)),
    notification_tool: NotificationTool = Depends(get_notification_tool),
):
    """
    Send ourself a test notification.

    **Only admins can use this endpoint**
    """
    message = schemas_notification.Message(
        context="notification-test",
        is_visible=True,
        title="Test notification",
        content="Ceci est un test de notification",
        # The notification will expire in 3 days
        expire_on=datetime.now(UTC) + timedelta(days=3),
    )
    await notification_tool.send_notification_to_user(
        user_id=user.id,
        message=message,
    )


@router.post(
    "/notification/send/future",
    status_code=201,
)
async def send_future_notification(
    user: models_core.CoreUser = Depends(is_user_in(GroupType.admin)),
    notification_tool: NotificationTool = Depends(get_notification_tool),
):
    """
    Send ourself a test notification.

    **Only admins can use this endpoint**
    """
    message = schemas_notification.Message(
        context="future-notification-test",
        is_visible=True,
        title="Test notification future",
        content="Ceci est un test de notification future",
        # The notification will expire in 3 days
        expire_on=datetime.now(UTC) + timedelta(days=3),
        delivery_datetime=datetime.now(UTC) + timedelta(minutes=3),
    )
    await notification_tool.send_notification_to_user(
        user_id=user.id,
        message=message,
    )


@router.get(
    "/notification/devices",
    status_code=200,
    response_model=list[schemas_notification.FirebaseDevice],
)
async def get_devices(
    user: models_core.CoreUser = Depends(is_user_in(GroupType.admin)),
    db: AsyncSession = Depends(get_db),
):
    """
    Get all devices a user have registered.
    This endpoint is useful to get firebase tokens for debugging purposes.

    **Only admins can use this endpoint**
    """
    return await cruds_notification.get_firebase_devices_by_user_id(
        user_id=user.id,
        db=db,
    )
