from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.feed import models_feed
from app.core.feed.types_feed import NewsStatus


async def create_news(
    news: models_feed.News,
    db: AsyncSession,
) -> None:
    """
    Create a news
    """

    db.add(news)


async def get_news(
    status: list[NewsStatus],
    db: AsyncSession,
) -> Sequence[models_feed.News]:
    result = await db.execute(
        select(models_feed.News).where(
            models_feed.News.status.in_(status),
        ),
    )
    return result.scalars().all()


async def get_all_news(
    db: AsyncSession,
) -> Sequence[models_feed.News]:
    result = await db.execute(select(models_feed.News))
    return result.scalars().all()


async def get_news_by_id(
    news_id: UUID,
    db: AsyncSession,
) -> models_feed.News | None:
    result = await db.execute(
        select(models_feed.News).where(
            models_feed.News.id == news_id,
        ),
    )
    return result.scalars().first()


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
