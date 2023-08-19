from datetime import date

from fastapi import APIRouter, Body, Depends, HTTPException
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
from app.utils.types.notification_types import Topic
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
            tokens=[firebase_token], topic=topic_membership.topic
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
            tokens=[firebase_token], topic=topic_membership.topic
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

    return await cruds_notification.get_messages_by_firebase_token(
        firebase_token=firebase_token, db=db
    )

    # TODO: remove messages after the client got them


@router.post(
    "/notification/topics/{topic}/subscribe",
    status_code=204,
    tags=[Tags.notifications],
)
async def suscribe_to_topic(
    topic: Topic,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
    notification_manager: NotificationManager = Depends(get_notification_manager),
):
    """
    Subscribe to a topic

    **The user must be authenticated to use this endpoint**
    """

    await notification_manager.subscribe_user_to_topic(
        user_id=user.id, topic=topic, db=db
    )


@router.post(
    "/notification/topics/{topic}/unsubscribe",
    status_code=204,
    tags=[Tags.notifications],
)
async def unsuscribe_to_topic(
    topic: Topic,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
    notification_manager: NotificationManager = Depends(get_notification_manager),
):
    """
    Unsubscribe to a topic

    **The user must be authenticated to use this endpoint**
    """

    await notification_manager.unsubscribe_user_to_topic(
        user_id=user.id, topic=topic, db=db
    )


@router.get(
    "/notification/topics",
    status_code=200,
    tags=[Tags.notifications],
    response_model=list[Topic],
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

    return [membership.topic for membership in memberships]


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
    Unsubscribe to a topic

    **The user must be authenticated to use this endpoint**
    """
    print("send notif")
    await notification_tool.send_notification_to_user(
        user_id=user.id,
        message=message,
    )
    print("send notif done")


@router.get(
    "/notification/devices",
    status_code=200,
    tags=[Tags.notifications],
)
async def get_tokens(
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin)),
    db: AsyncSession = Depends(get_db),
):
    """
    Unsubscribe to a topic

    **The user must be authenticated to use this endpoint**
    """
    return await cruds_notification.get_firebase_devices_by_user_id(
        user_id=user.id, db=db
    )
