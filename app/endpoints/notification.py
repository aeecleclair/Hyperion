from datetime import date, datetime

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
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
    "/notification/register-device",
    response_model=schemas_notification.FirebaseDevice,
    status_code=201,
    tags=[Tags.notifications],
)
async def register_firebase_device(
    firebase_token: str = Body(embed=True),
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Register a new firebase device for the user

    **The user must be authenticated to use this endpoint**
    """
    firebase_device = models_notification.FirebaseDevice(
        user_id=user.id,
        firebase_device_token=firebase_token,
        creation_date=date.today(),
    )

    try:
        result = await cruds_notification.create_firebase_devices(
            firebase_device=firebase_device, db=db
        )
        return result
    except IntegrityError as error:
        raise HTTPException(status_code=400, detail=str(error))


@router.post(
    "/notification/unregister-device",
    response_model=schemas_notification.FirebaseDevice,
    status_code=201,
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

    try:
        result = await cruds_notification.delete_firebase_devices(
            user_id=user.id, firebase_device_token=firebase_token, db=db
        )
    except IntegrityError as error:
        raise HTTPException(status_code=400, detail=str(error))


@router.get(
    "/notification/messages/{firebase_token}",
    response_model=schemas_notification.FirebaseDevice,
    status_code=201,
    tags=[Tags.notifications],
)
async def get_messages(
    firebase_token: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Get all messages for a specific device from the user

    **The user must be authenticated to use this endpoint**
    """
    firebase_device = (
        cruds_notification.get_firebase_devices_by_user_id_and_firebase_token(
            user_id=user.id, firebase_token=firebase_token, db=db
        )
    )

    if firebase_device is None:
        raise HTTPException(
            status_code=404, detail=f"Device not found for user {user.id}"
        )

    return cruds_notification.get_messages_by_firebase_token(
        firebase_token=firebase_token, db=db
    )


@router.post(
    "/notification/topics/{topic}/subscribe",
    response_model=schemas_notification.FirebaseDevice,
    status_code=201,
    tags=[Tags.notifications],
)
async def suscribe_to_topic(
    topic: Topic,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Subscribe to a topic

    **The user must be authenticated to use this endpoint**
    """
    topic_membership = models_notification.TopicMembership(user_id=user.id, topic=topic)

    # TODO: firebase topic subscription

    try:
        result = await cruds_notification.create_topic_membership(
            topic_membership=topic_membership, db=db
        )
        return result
    except IntegrityError as error:
        raise HTTPException(status_code=400, detail=str(error))


@router.post(
    "/notification/topics/{topic}/unsubscribe",
    response_model=schemas_notification.FirebaseDevice,
    status_code=201,
    tags=[Tags.notifications],
)
async def unsuscribe_to_topic(
    topic: Topic,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Unsubscribe to a topic

    **The user must be authenticated to use this endpoint**
    """

    # TODO: firebase topic subscription

    try:
        result = await cruds_notification.delete_topic_membership(
            topic=topic, user_id=user.id, db=db
        )
        return result
    except IntegrityError as error:
        raise HTTPException(status_code=400, detail=str(error))


@router.post(
    "/notification/topics/send",
    status_code=201,
    tags=[Tags.notifications],
)
async def send_notif(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin)),
    notif_manager: NotificationManager = Depends(get_notification_manager),
):
    """
    Unsubscribe to a topic

    **The user must be authenticated to use this endpoint**
    """
    print("send notif")
    await notif_manager.send_notification_to_user(
        user_id=user.id,
        message=schemas_notification.Message(
            title="Hello world",
            content="test",
            context="test",
            action_id="test",
            expire_on=datetime.now(),
            is_visible=True,
        ),
    )
    print("send notif done")
