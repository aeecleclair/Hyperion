from collections.abc import Sequence
from datetime import date

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.notification import models_notification
from app.core.notification.notification_types import CustomTopic, Topic


async def get_firebase_devices_by_user_id(
    user_id: str,
    db: AsyncSession,
) -> Sequence[models_notification.FirebaseDevice]:
    result = await db.execute(
        select(models_notification.FirebaseDevice).where(
            models_notification.FirebaseDevice.user_id == user_id,
        ),
    )
    return result.scalars().all()


async def get_firebase_devices_by_user_id_and_firebase_token(
    # If we want to enable authentification for /messages/{firebase_token} endpoint, we may to uncomment the following line
    # user_id: str,
    firebase_token: str,
    db: AsyncSession,
) -> models_notification.FirebaseDevice | None:
    result = await db.execute(
        select(models_notification.FirebaseDevice).where(
            # If we want to enable authentification for /messages/{firebase_token} endpoint, we may to uncomment the following line
            # models_notification.FirebaseDevice.user_id == user_id,
            models_notification.FirebaseDevice.firebase_device_token == firebase_token,
        ),
    )
    return result.scalars().first()


async def get_firebase_devices_by_firebase_token(
    firebase_token: str,
    db: AsyncSession,
) -> models_notification.FirebaseDevice | None:
    result = await db.execute(
        select(models_notification.FirebaseDevice).where(
            models_notification.FirebaseDevice.firebase_device_token == firebase_token,
        ),
    )
    return result.scalars().first()


async def create_firebase_devices(
    firebase_device: models_notification.FirebaseDevice,
    db: AsyncSession,
) -> models_notification.FirebaseDevice:
    """Register a new firebase device in database and return it"""

    db.add(firebase_device)
    await db.flush()
    return firebase_device


async def delete_firebase_devices(
    firebase_device_token: str,
    db: AsyncSession,
):
    await db.execute(
        delete(models_notification.FirebaseDevice).where(
            models_notification.FirebaseDevice.firebase_device_token
            == firebase_device_token,
        ),
    )
    await db.flush()


async def batch_delete_firebase_device_by_token(
    tokens: list[str],
    db: AsyncSession,
):
    await db.execute(
        delete(models_notification.FirebaseDevice).where(
            models_notification.FirebaseDevice.firebase_device_token.in_(tokens),
        ),
    )
    await db.flush()


async def update_firebase_devices_register_date(
    firebase_device_token: str,
    new_register_date: date,
    db: AsyncSession,
):
    await db.execute(
        update(models_notification.FirebaseDevice)
        .where(
            models_notification.FirebaseDevice.firebase_device_token
            == firebase_device_token,
        )
        .values({"register_date": new_register_date}),
    )
    await db.flush()


async def create_topic_membership(
    topic_membership: models_notification.TopicMembership,
    db: AsyncSession,
) -> models_notification.TopicMembership:
    db.add(topic_membership)
    await db.flush()
    return topic_membership


async def delete_topic_membership(
    user_id: str,
    custom_topic: CustomTopic,
    db: AsyncSession,
):
    await db.execute(
        delete(models_notification.TopicMembership).where(
            models_notification.TopicMembership.user_id == user_id,
            models_notification.TopicMembership.topic == custom_topic.topic,
            models_notification.TopicMembership.topic_identifier
            == custom_topic.topic_identifier,
        ),
    )
    await db.flush()


async def get_topic_memberships_by_topic(
    custom_topic: CustomTopic,
    db: AsyncSession,
) -> Sequence[models_notification.TopicMembership]:
    result = await db.execute(
        select(models_notification.TopicMembership).where(
            models_notification.TopicMembership.topic == custom_topic.topic,
            models_notification.TopicMembership.topic_identifier
            == custom_topic.topic_identifier,
        ),
    )
    return result.scalars().all()


async def get_topic_memberships_by_user_id(
    user_id: str,
    db: AsyncSession,
) -> Sequence[models_notification.TopicMembership]:
    result = await db.execute(
        select(models_notification.TopicMembership).where(
            models_notification.TopicMembership.user_id == user_id,
        ),
    )
    return result.scalars().all()


async def get_topic_memberships_with_identifiers_by_user_id_and_topic(
    user_id: str,
    topic: Topic,
    db: AsyncSession,
) -> Sequence[models_notification.TopicMembership]:
    result = await db.execute(
        select(models_notification.TopicMembership).where(
            models_notification.TopicMembership.user_id == user_id,
            models_notification.TopicMembership.topic == topic,
            models_notification.TopicMembership.topic_identifier != "",
        ),
    )
    return result.scalars().all()


async def get_topic_membership_by_user_id_and_custom_topic(
    user_id: str,
    custom_topic: CustomTopic,
    db: AsyncSession,
) -> models_notification.TopicMembership | None:
    result = await db.execute(
        select(models_notification.TopicMembership).where(
            models_notification.TopicMembership.user_id == user_id,
            models_notification.TopicMembership.topic == custom_topic.topic,
            models_notification.TopicMembership.topic_identifier
            == custom_topic.topic_identifier,
        ),
    )
    return result.scalars().first()


async def get_user_ids_by_topic(
    custom_topic: CustomTopic,
    db: AsyncSession,
) -> list[str]:
    result = await db.execute(
        select(models_notification.TopicMembership.user_id).where(
            models_notification.TopicMembership.topic == custom_topic.topic,
            models_notification.TopicMembership.topic_identifier
            == custom_topic.topic_identifier,
        ),
    )
    return list(result.scalars().all())


async def get_firebase_tokens_by_user_ids(
    user_ids: list[str],
    db: AsyncSession,
) -> list[str]:
    result = await db.execute(
        select(models_notification.FirebaseDevice.firebase_device_token).where(
            models_notification.FirebaseDevice.user_id.in_(user_ids),
        ),
    )
    return list(result.scalars().all())
