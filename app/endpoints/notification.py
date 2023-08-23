from datetime import date

from fastapi import APIRouter, Body, Depends, HTTPException, Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.cruds import cruds_notification
from app.dependencies import (
    get_db,
    get_notification_manager,
    get_notification_tool,
    is_user_a_member,
    is_user_a_member_of,
)
from app.models import models_core, models_notification
from app.schemas import schemas_notification
from app.utils.communication.notifications import NotificationManager, NotificationTool
from app.utils.types.groups_type import GroupType
from app.utils.types.notification_types import CustomTopic, Topic
from app.utils.types.tags import Tags

router = APIRouter()


@router.post(
    "/notification/devices",
    status_code=204,
    tags=[Tags.notifications],
)
async def register_firebase_device(
    firebase_token: str = Body(embed=True),
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
    notification_manager: NotificationManager = Depends(get_notification_manager),
):
    """
    Register a firebase device for the user, if the device already exists, this will update the creation date.
    This endpoint should be called once a month to ensure that the token is still valide.

    **The user must be authenticated to use this endpoint**
    """

    # If there is already a device with this token, we need to update the register date
    firebase_device = await cruds_notification.get_firebase_devices_by_firebase_token(
        firebase_token=firebase_token, db=db
    )

    if firebase_device is not None:
        if firebase_device.user_id == user.id:
            # Update the register date
            await cruds_notification.update_firebase_devices_register_date(
                firebase_device_token=firebase_token,
                new_register_date=date.today(),
                db=db,
            )
            return
        # If the user is not the same, we don't want the new user to receive the notifications of the old one
        await cruds_notification.delete_firebase_devices(
            firebase_device_token=firebase_token, db=db
        )

    # We also need to subscribe the new token to the topics the user is subscribed to
    topic_memberships = await cruds_notification.get_topic_membership_by_user_id(
        user_id=user.id, db=db
    )

    for topic_membership in topic_memberships:
        await notification_manager.subscribe_tokens_to_topic(
            tokens=[firebase_token],
            custom_topic=CustomTopic(
                topic=topic_membership.topic,
                topic_identifier=topic_membership.topic_identifier,
            ),
        )

    firebase_device = models_notification.FirebaseDevice(
        user_id=user.id,
        firebase_device_token=firebase_token,
        register_date=date.today(),
    )

    await cruds_notification.create_firebase_devices(
        firebase_device=firebase_device, db=db
    )


@router.delete(
    "/notification/devices/{firebase_token}",
    status_code=204,
    tags=[Tags.notifications],
)
async def unregister_firebase_device(
    firebase_token: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
    notification_manager: NotificationManager = Depends(get_notification_manager),
):
    """
    Unregister a new firebase device for the user

    **The user must be authenticated to use this endpoint**
    """
    # Anybody may unregister a device if they know its token, which should be secret

    # We also need to unsubscribe the token to the topics the user is subscribed to
    topic_memberships = await cruds_notification.get_topic_membership_by_user_id(
        user_id=user.id, db=db
    )

    for topic_membership in topic_memberships:
        await notification_manager.unsubscribe_tokens_to_topic(
            tokens=[firebase_token],
            custom_topic=CustomTopic(
                topic=topic_membership.topic,
                topic_identifier=topic_membership.topic_identifier,
            ),
        )

    await cruds_notification.delete_firebase_devices(
        firebase_device_token=firebase_token, db=db
    )


@router.get(
    "/notification/messages/{firebase_token}",
    response_model=list[schemas_notification.Message],
    status_code=200,
    tags=[Tags.notifications],
)
async def get_messages(
    firebase_token: str,
    db: AsyncSession = Depends(get_db),
    #    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Get all messages for a specific device from the user

    **The user must be authenticated to use this endpoint**
    """
    # TODO: enable authentification for this endpoint
    firebase_device = (
        await cruds_notification.get_firebase_devices_by_user_id_and_firebase_token(
            firebase_token=firebase_token, db=db  # user_id=user.id,
        )
    )

    if firebase_device is None:
        raise HTTPException(
            status_code=404, detail="Device not found for user"  # {user.id}"
        )

    messages = await cruds_notification.get_messages_by_firebase_token(
        firebase_token=firebase_token, db=db
    )

    await cruds_notification.remove_message_by_firebase_device_token(
        firebase_device_token=firebase_token, db=db
    )

    return messages


@router.post(
    "/notification/topics/{topic_str}/subscribe",
    status_code=204,
    tags=[Tags.notifications],
)
async def suscribe_to_topic(
    topic_str: str = Path(
        description="The topic to subscribe to (the Topic may be followed by an additional identifier)",
        example="cinema_4c029b5f-2bf7-4b70-85d4-340a4bd28653",
    ),
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
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
        user_id=user.id, custom_topic=custom_topic, db=db
    )


@router.post(
    "/notification/topics/{topic_str}/unsubscribe",
    status_code=204,
    tags=[Tags.notifications],
)
async def unsuscribe_to_topic(
    topic_str: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
    notification_manager: NotificationManager = Depends(get_notification_manager),
):
    """
    Unsubscribe to a topic

    **The user must be authenticated to use this endpoint**
    """

    custom_topic = CustomTopic.from_str(topic_str)

    await notification_manager.unsubscribe_user_to_topic(
        user_id=user.id, custom_topic=custom_topic, db=db
    )


@router.get(
    "/notification/topics",
    status_code=200,
    tags=[Tags.notifications],
    response_model=list[str],
)
async def get_topic(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Get topics the user is subscribed to

    **The user must be authenticated to use this endpoint**
    """

    memberships = await cruds_notification.get_topic_membership_by_user_id(
        user_id=user.id, db=db
    )

    return [
        CustomTopic(
            topic=membership.topic, topic_identifier=membership.topic_identifier
        ).to_str()
        for membership in memberships
    ]


@router.post(
    "/notification/send",
    status_code=201,
    tags=[Tags.notifications],
)
async def send_notif(
    message: schemas_notification.Message,
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin)),
    notification_tool: NotificationTool = Depends(get_notification_tool),
):
    """
    Send ourself a test notification.

    **Only admins can use this endpoint**
    """
    await notification_tool.send_notification_to_user(
        user_id=user.id,
        message=message,
    )


@router.get(
    "/notification/devices",
    status_code=200,
    response_model=list[schemas_notification.FirebaseDevice],
    tags=[Tags.notifications],
)
async def get_devices(
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin)),
    db: AsyncSession = Depends(get_db),
):
    """
    Get all devices a user have registered.
    This endpoint is useful to get firebase tokens for debugging purposes.

    **Only admins can use this endpoint**
    """
    return await cruds_notification.get_firebase_devices_by_user_id(
        user_id=user.id, db=db
    )
