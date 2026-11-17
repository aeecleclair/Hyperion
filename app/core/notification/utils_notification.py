from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import schemas_auth
from app.core.groups.groups_type import AccountType
from app.core.notification import cruds_notification, schemas_notification
from app.core.notification.models_notification import NotificationTopic
from app.utils.tools import is_user_token_from_any_group


async def get_user_notification_topics(
    token: schemas_auth.TokenData,
    db: AsyncSession,
) -> list[schemas_notification.TopicUser]:
    """
    Return the list of all topics a user may subscribe to, and if it is currently subscribed
    """
    topics = await cruds_notification.get_notification_topic(
        db=db,
    )

    memberships = await cruds_notification.get_topic_memberships_by_user_id(
        user_id=token.id,
        db=db,
    )

    subscribed_topic_ids = [membership.topic_id for membership in memberships]

    result: list[schemas_notification.TopicUser] = []

    for topic in topics:
        if topic.restrict_to_members:
            if token.account_type == AccountType.external:
                continue
        if topic.restrict_to_group_id:
            if not is_user_token_from_any_group(
                token=token,
                allowed_groups=[topic.restrict_to_group_id],
            ):
                continue

        result.append(
            schemas_notification.TopicUser(
                id=topic.id,
                name=topic.name,
                module_root=topic.module_root,
                topic_identifier=topic.topic_identifier,
                is_user_subscribed=topic.id in subscribed_topic_ids,
            ),
        )

    return result


async def get_topics_restricted_to_group_id(
    group_id: str,
    db: AsyncSession,
) -> Sequence[NotificationTopic]:
    return await cruds_notification.get_topics_restricted_to_group_id(
        group_id=group_id,
        db=db,
    )


async def get_topic_by_root_and_identifier(
    module_root: str,
    topic_identifier: str | None,
    db: AsyncSession,
) -> NotificationTopic | None:
    return await cruds_notification.get_notification_topic_by_root_and_identifier(
        module_root=module_root,
        topic_identifier=topic_identifier,
        db=db,
    )
