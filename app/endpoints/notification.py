from datetime import date, datetime

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.cruds import cruds_notification
from app.dependencies import (
    get_db,
    get_notification_manager,
    is_user_a_member,
    is_user_a_member_of,
)
from app.models import models_core, models_notification
from app.schemas import schemas_notification
from app.utils.communication.notifications import NotificationManager
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
):
    """
    Register a firebase device for the user, if the device already exists, this will update the creation date.
    This endpoint should be called once a month to ensure that the token is still valide.

    **The user must be authenticated to use this endpoint**
    """

    # If there is already a device with this token, we want to remove it
    #  - If the user is not the same, we indeed don't want the new user to receive the notifications of the old one
    #  - If the user is the same, a new device will be created with a new creation date
    await cruds_notification.delete_firebase_devices(
        firebase_device_token=firebase_token, db=db
    )

    firebase_device = models_notification.FirebaseDevice(
        user_id=user.id,
        firebase_device_token=firebase_token,
        creation_date=date.today(),
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
):
    """
    Unregister a new firebase device for the user

    **The user must be authenticated to use this endpoint**
    """
    # Anybody may unregister a device if they know its token
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
    topic_membership = models_notification.TopicMembership(user_id=user.id, topic=topic)

    await notification_manager.subscribe_user_to_topic(user_id=user.id, topic=topic)

    await cruds_notification.create_topic_membership(
        topic_membership=topic_membership, db=db
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

    await notification_manager.unsubscribe_user_to_topic(user_id=user.id, topic=topic)

    await cruds_notification.delete_topic_membership(
        topic=topic, user_id=user.id, db=db
    )


@router.post(
    "/notification/topics/send",
    status_code=201,
    tags=[Tags.notifications],
)
async def send_notif(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin)),
    notification_manager: NotificationManager = Depends(get_notification_manager),
):
    """
    Unsubscribe to a topic

    **The user must be authenticated to use this endpoint**
    """
    print("send notif")
    await notification_manager.send_notification_to_user(
        user_id=user.id,
        message=schemas_notification.Message(
            title="Hello world!",
            content="test",
            context="test2",
            action_id="test",
            expire_on=datetime.now(),
            is_visible=True,
        ),
    )
    print("send notif done")
