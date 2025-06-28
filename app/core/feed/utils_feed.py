import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.feed import cruds_feed, schemas_feed
from app.core.feed.types_feed import NewsStatus
from app.core.groups.groups_type import GroupType
from app.core.notification.schemas_notification import Message
from app.utils.communication.notifications import NotificationTool


async def create_feed_news(
    title: str,
    start: str,
    end: str | None,
    entity: str,
    module: str,
    module_object_id: uuid.UUID,
    image_folder: str,
    image_id: uuid.UUID,
    require_feed_admin_approval: bool,
    db: AsyncSession,
    notification_tool: NotificationTool,
):
    """
    Create a news in the feed

    title: title of the news,
    start: datetime corresponding to the start of the news. The news should be visible at this day
    end: optional end datetime, may be used to compute the news subtitle
    entity: name of the entity that created the news, usually the name of an association or a group
    module: identifier of the module that created the news, may be used to open the right page in the app
    module_object_id: identifier of the object that is linked to the news in the module, may be used to open the right page in the app
    image_folder: folder where the image is stored, used to display the image in the news
    image_id: uuid of the image is stored, used to display the image in the news,
    require_feed_admin_approval: if the news can be published directly or if it requires approval from a feed administrator
    """

    news = schemas_feed.News(
        id=uuid.uuid4(),
        title=title,
        start=start,
        end=end,
        entity=entity,
        module=module,
        module_object_id=module_object_id,
        image_folder=image_folder,
        image_id=image_id,
        status=NewsStatus.WAITING_APPROVAL
        if require_feed_admin_approval
        else NewsStatus.PUBLISHED,
    )
    await cruds_feed.create_news(news=news, db=db)

    if require_feed_admin_approval:
        message = Message(
            title="🔔 Feed - a news require approval",
            content=f"{entity} has created {title}",
            action_module="feed",
        )
        await notification_tool.send_notification_to_group(
            group_id=GroupType.feed_admin,
            message=message,
        )
