from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import models_notification
from app.utils.types.notification_types import Topic


async def create_message(
    message: models_notification.Message,
    db: AsyncSession,
) -> None:
    """Create a new raffle in database and return it"""

    db.add(message)
    try:
        await db.commit()
    except IntegrityError as err:
        await db.rollback()
        raise err


async def get_messages_by_firebase_token(
    firebase_token: str,
    db: AsyncSession,
) -> list[models_notification.Message]:
    """Create a new raffle in database and return it"""

    result = await db.execute(
        select(models_notification.Message).where(
            models_notification.Message.firebase_device_token == firebase_token
        )
    )
    return result.scalars().all()


async def get_firebase_devices_by_user_id(
    user_id: str,
    db: AsyncSession,
) -> list[models_notification.FirebaseDevice]:
    """Return the loaner with id"""

    result = await db.execute(
        select(models_notification.FirebaseDevice).where(
            models_notification.FirebaseDevice.user_id == user_id
        )
    )
    return result.scalars().all()


async def get_firebase_devices_by_user_id_and_firebase_token(
    user_id: str,
    firebase_token: str,
    db: AsyncSession,
) -> models_notification.FirebaseDevice | None:
    """Return the loaner with id"""

    result = await db.execute(
        select(models_notification.FirebaseDevice).where(
            models_notification.FirebaseDevice.user_id == user_id,
            models_notification.FirebaseDevice.firebase_device_token == firebase_token,
        )
    )
    return result.scalars().first()


async def create_firebase_devices(
    firebase_device: models_notification.FirebaseDevice,
    db: AsyncSession,
) -> models_notification.FirebaseDevice:
    """Register a new firebase device in database and return it"""

    db.add(firebase_device)
    try:
        await db.commit()
        return firebase_device
    except IntegrityError as error:
        await db.rollback()
        raise ValueError(error)


async def delete_firebase_devices(
    user_id: str,
    firebase_device_token: str,
    db: AsyncSession,
):
    await db.execute(
        delete(models_notification.FirebaseDevice).where(
            models_notification.FirebaseDevice.user_id == user_id,
            models_notification.FirebaseDevice.firebase_device_token
            == firebase_device_token,
        )
    )
    await db.commit()


async def create_topic_membership(
    topic_membership: models_notification.TopicMembership,
    db: AsyncSession,
) -> models_notification.TopicMembership:
    """Register a new firebase device in database and return it"""

    db.add(topic_membership)
    try:
        await db.commit()
        return topic_membership
    except IntegrityError as error:
        await db.rollback()
        raise ValueError(error)


async def delete_topic_membership(
    user_id: str,
    topic: str,
    db: AsyncSession,
):
    await db.execute(
        delete(models_notification.TopicMembership).where(
            models_notification.TopicMembership.user_id == user_id,
            models_notification.TopicMembership.topic == topic,
        )
    )
    await db.commit()


async def get_topic_membership_by_topic(
    topic: Topic,
    db: AsyncSession,
) -> list[models_notification.TopicMembership]:
    """Return the loaner with id"""

    result = await db.execute(
        select(models_notification.TopicMembership).where(
            models_notification.TopicMembership.topic == topic
        )
    )
    return result.scalars().all()
