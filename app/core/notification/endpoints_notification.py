from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Body, Depends, HTTPException, Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.groups.groups_type import GroupType
from app.core.notification import (
    cruds_notification,
    models_notification,
    schemas_notification,
)
from app.core.notification.notification_types import CustomTopic, Topic
from app.core.users import models_users
from app.dependencies import (
    get_db,
    get_notification_manager,
    get_notification_tool,
    get_scheduler,
    is_user,
    is_user_in,
)
from app.types.module import CoreModule
from app.types.scheduler import Scheduler
from app.utils.communication.notifications import NotificationManager, NotificationTool

router = APIRouter(tags=["Notifications"])

core_module = CoreModule(
    root="notification",
    tag="Notifications",
    router=router,
)


@router.post(
    "/notification/devices",
    status_code=204,
)
async def register_firebase_device(
    firebase_token: str = Body(embed=True),
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user()),
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

    user_topics = await cruds_notification.get_topic_memberships_by_user_id(
        user_id=user.id,
        db=db,
    )
    for topic in user_topics:
        await notification_manager.subscribe_tokens_to_topic(
            custom_topic=CustomTopic(topic.topic),
            tokens=[firebase_token],
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
    user: models_users.CoreUser = Depends(is_user()),
    notification_manager: NotificationManager = Depends(get_notification_manager),
):
    """
    Unregister a firebase device for the user

    **The user must be authenticated to use this endpoint**
    """
    # Anybody may unregister a device if they know its token, which should be secret

    await cruds_notification.delete_firebase_devices(
        firebase_device_token=firebase_token,
        db=db,
    )

    user_topics = await cruds_notification.get_topic_memberships_by_user_id(
        user_id=user.id,
        db=db,
    )
    for topic in user_topics:
        await notification_manager.unsubscribe_tokens_to_topic(
            topic_id=topic.id,
            tokens=[firebase_token],
        )


@router.post(
    "/notification/topics/{topic_id}/subscribe",
    status_code=204,
)
async def subscribe_to_topic(
    topic_id: str = Path(),
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user()),
    notification_manager: NotificationManager = Depends(get_notification_manager),
):
    """
    Subscribe to a topic

    **The user must be authenticated to use this endpoint**
    """

    await notification_manager.subscribe_user_to_topic(
        user_id=user.id,
        topic_id=topic_id,
        db=db,
    )


@router.post(
    "/notification/topics/{topic_str}/unsubscribe",
    status_code=204,
)
async def unsubscribe_to_topic(
    topic_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user()),
    notification_manager: NotificationManager = Depends(get_notification_manager),
):
    """
    Unsubscribe to a topic

    **The user must be authenticated to use this endpoint**
    """

    await notification_manager.unsubscribe_user_to_topic(
        user_id=user.id,
        topic_id=topic_id,
        db=db,
    )


@router.get(
    "/notification/topics",
    status_code=200,
    response_model=list[str],
)
async def get_topic(
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user()),
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

    topics = []
    for membership in memberships:
        topic = await cruds_notification.get_topic_by_id(membership.topic_id, db)
        topics.append(topic.name)

    return topics


@router.get(
    "/notification/topics/{topic}",
    status_code=200,
    response_model=list[str],
)
async def get_topic_identifier(
    topic: Topic,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user()),
):
    """
    Get custom topic (with identifiers) the user is subscribed to

    **The user must be authenticated to use this endpoint**
    """

    memberships = await cruds_notification.get_topic_memberships_with_identifiers_by_user_id_and_topic(
        user_id=user.id,
        db=db,
        topic_id=topic_id,
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
    status_code=204,
)
async def send_notification(
    notification_request: schemas_notification.GroupNotificationRequest,
    user: models_users.CoreUser = Depends(is_user_in(GroupType.admin)),
    notification_tool: NotificationTool = Depends(get_notification_tool),
):
    """
    Send a notification to a group.

    **Only admins can use this endpoint**
    """
    message = schemas_notification.Message(
        title=notification_request.title,
        content=notification_request.content,
        action_module="",
    )
    await notification_tool.send_notification_to_group(
        group_id=notification_request.group_id,
        message=message,
    )


@router.post(
    "/notification/test/send",
    status_code=201,
)
async def send_test_notification(
    user: models_users.CoreUser = Depends(is_user_in(GroupType.admin)),
    notification_tool: NotificationTool = Depends(get_notification_tool),
):
    """
    Send ourself a test notification.

    **Only admins can use this endpoint**
    """
    message = schemas_notification.Message(
        title="Test notification",
        content="Ceci est un test de notification",
        action_module="test",
    )
    await notification_tool.send_notification_to_user(
        user_id=user.id,
        message=message,
    )


@router.post(
    "/notification/test/send/future",
    status_code=204,
)
async def send_test_future_notification(
    user: models_users.CoreUser = Depends(is_user_in(GroupType.admin)),
    notification_tool: NotificationTool = Depends(get_notification_tool),
    scheduler: Scheduler = Depends(get_scheduler),
):
    """
    Send ourself a test notification.

    **Only admins can use this endpoint**
    """
    message = schemas_notification.Message(
        title="Test notification future",
        content="Ceci est un test de notification future",
        action_module="test",
    )
    await notification_tool.send_notification_to_users(
        user_ids=[user.id],
        message=message,
        defer_date=datetime.now(UTC) + timedelta(seconds=10),
        scheduler=scheduler,
        job_id="testtt",
    )


@router.post(
    "/notification/test/send/topic",
    status_code=204,
)
async def send_test_notification_topic(
    user: models_users.CoreUser = Depends(is_user_in(GroupType.admin)),
    notification_tool: NotificationTool = Depends(get_notification_tool),
):
    """
    Send ourself a test notification.

    **Only admins can use this endpoint**
    """
    message = schemas_notification.Message(
        title="Test notification topic",
        content="Ceci est un test de notification topic",
        action_module="test",
    )
    await notification_tool.send_notification_to_topic(
        custom_topic=CustomTopic.from_str("test"),
        message=message,
    )


@router.post(
    "/notification/test/send/topic/future",
    status_code=204,
)
async def send_test_future_notification_topic(
    user: models_users.CoreUser = Depends(is_user_in(GroupType.admin)),
    notification_tool: NotificationTool = Depends(get_notification_tool),
    scheduler: Scheduler = Depends(get_scheduler),
):
    """
    Send ourself a test notification.

    **Only admins can use this endpoint**
    """
    message = schemas_notification.Message(
        title="Test notification future topic",
        content="Ceci est un test de notification future topic",
        action_module="test",
    )
    await notification_tool.send_notification_to_topic(
        custom_topic=CustomTopic.from_str("test"),
        message=message,
        defer_date=datetime.now(UTC) + timedelta(seconds=10),
        job_id="test26",
        scheduler=scheduler,
    )


@router.get(
    "/notification/devices",
    status_code=200,
    response_model=list[schemas_notification.FirebaseDevice],
)
async def get_devices(
    user: models_users.CoreUser = Depends(is_user_in(GroupType.admin)),
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
