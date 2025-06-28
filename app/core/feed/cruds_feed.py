from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.feed import models_feed, schemas_feed
from app.core.feed.types_feed import NewsStatus


async def create_news(
    news: schemas_feed.News,
    db: AsyncSession,
) -> None:
    """
    Create a news
    """
    news_model = models_feed.News(
        id=news.id,
        title=news.title,
        start=news.start,
        end=news.end,
        entity=news.entity,
        module=news.module,
        module_object_id=news.module_object_id,
        image_folder=news.image_folder,
        image_id=news.image_id,
        status=news.status,
    )
    db.add(news_model)


async def get_news(
    status: list[NewsStatus],
    db: AsyncSession,
) -> list[schemas_feed.News]:
    result = await db.execute(
        select(models_feed.News).where(
            models_feed.News.status.in_(status),
        ),
    )
    return [
        schemas_feed.News(
            id=news.id,
            title=news.title,
            start=news.start,
            end=news.end,
            entity=news.entity,
            module=news.module,
            module_object_id=news.module_object_id,
            image_folder=news.image_folder,
            image_id=news.image_id,
            status=news.status,
        )
        for news in result.scalars().all()
    ]


async def change_news_status(
    news_id: UUID,
    status: NewsStatus,
    db: AsyncSession,
) -> None:
    await db.execute(
        update(models_feed.News)
        .where(models_feed.News.id == news_id)
        .values(status=status),
    )
