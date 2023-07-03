from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.cruds import cruds_notification
from app.dependencies import get_db, is_user_a_member
from app.models import models_core, models_notification
from app.schemas import schemas_notification
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
    firebase_token: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Register a new firebase device for the user

    **The user must be authenticated to use this endpoint**
    """
    firebase_device = models_notification.FirebaseDevice(
        user_id=user.id, firebase_device_token=firebase_token
    )

    try:
        result = await cruds_notification.create_firebase_devices(
            firebase_device=firebase_device, db=db
        )
        return result
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

    try:
        result = await cruds_notification.delete_topic_membership(
            topic=topic, user_id=user.id, db=db
        )
        return result
    except IntegrityError as error:
        raise HTTPException(status_code=400, detail=str(error))
