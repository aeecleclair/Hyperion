from collections.abc import Sequence
from datetime import date
from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.notification import models_notification


async def get_notification_topic(
    db: AsyncSession,
) -> Sequence[models_notification.NotificationTopic]:
    result = await db.execute(select(models_notification.NotificationTopic))
    return result.scalars().all()


async def get_notification_topic_by_id(
    topic_id: UUID,
    db: AsyncSession,
) -> models_notification.NotificationTopic | None:
    result = await db.execute(
        select(models_notification.NotificationTopic).where(
            models_notification.NotificationTopic.id == topic_id,
        ),
    )
    return result.scalars().first()


async def get_topics_restricted_to_group_id(
    group_id: str,
    db: AsyncSession,
) -> Sequence[models_notification.NotificationTopic]:
    result = await db.execute(
        select(models_notification.NotificationTopic).where(
            models_notification.NotificationTopic.restrict_to_group_id == group_id,
        ),
    )
    return result.scalars().all()


async def get_notification_topic_by_root_and_identifier(
    module_root: str,
    topic_identifier: str | None,
    db: AsyncSession,
) -> models_notification.NotificationTopic | None:
    result = await db.execute(
        select(models_notification.NotificationTopic).where(
            models_notification.NotificationTopic.module_root == module_root,
            models_notification.NotificationTopic.topic_identifier == topic_identifier,
        ),
    )
    return result.scalars().first()


async def create_notification_topic(
    notification_topic: models_notification.NotificationTopic,
    db: AsyncSession,
) -> None:
    """Register a new topic in database and return it"""

    db.add(notification_topic)
    await db.flush()


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
    topic_id: UUID,
    db: AsyncSession,
):
    await db.execute(
        delete(models_notification.TopicMembership).where(
            models_notification.TopicMembership.user_id == user_id,
            models_notification.TopicMembership.topic_id == topic_id,
        ),
    )
    await db.flush()


async def get_topic_memberships_by_topic_id(
    topic_id: str,
    db: AsyncSession,
) -> Sequence[models_notification.TopicMembership]:
    result = await db.execute(
        select(models_notification.TopicMembership).where(
            models_notification.TopicMembership.topic_id == topic_id,
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


async def get_topic_memberships_with_identifiers_by_user_id_and_topic_id(
    user_id: str,
    topic_id: str,
    db: AsyncSession,
) -> Sequence[models_notification.TopicMembership]:
    result = await db.execute(
        select(models_notification.TopicMembership).where(
            models_notification.TopicMembership.user_id == user_id,
            models_notification.TopicMembership.topic_id == topic_id,
        ),
    )
    return result.scalars().all()


async def get_topic_membership_by_user_id_and_topic_id(
    user_id: str,
    topic_id: UUID,
    db: AsyncSession,
) -> models_notification.TopicMembership | None:
    result = await db.execute(
        select(models_notification.TopicMembership).where(
            models_notification.TopicMembership.user_id == user_id,
            models_notification.TopicMembership.topic_id == topic_id,
        ),
    )
    return result.scalars().first()


async def get_user_ids_by_topic_id(
    topic_id: UUID,
    db: AsyncSession,
) -> list[str]:
    result = await db.execute(
        select(models_notification.TopicMembership.user_id).where(
            models_notification.TopicMembership.topic_id == topic_id,
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


async def get_user_ids_by_firebase_tokens(
    tokens: list[str],
    db: AsyncSession,
) -> list[str]:
    result = await db.execute(
        select(models_notification.FirebaseDevice.user_id).where(
            models_notification.FirebaseDevice.firebase_device_token.in_(tokens),
        ),
    )
    return list(result.scalars().all())
