from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.feed import models_feed, schemas_feed
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


async def update_news_module_and_object_id(
    module: str,
    module_object_id: UUID,
    new_module: str,
    new_module_object_id: UUID,
    db: AsyncSession,
) -> None:
    """
    Change the module and module_object_id of a news in the feed
    """
    await db.execute(
        update(models_feed.News)
        .where(
            models_feed.News.module == module,
            models_feed.News.module_object_id == module_object_id,
        )
        .values(
            module=new_module,
            module_object_id=new_module_object_id,
        ),
    )


async def change_news_status_by_module_object_id(
    module: str,
    module_object_id: UUID,
    status: NewsStatus,
    db: AsyncSession,
) -> None:
    await db.execute(
        update(models_feed.News)
        .where(
            models_feed.News.module == module,
            models_feed.News.module_object_id == module_object_id,
        )
        .values(status=status),
    )


async def edit_news_by_module_object_id(
    module: str,
    module_object_id: UUID,
    news_edit: schemas_feed.NewsEdit,
    db: AsyncSession,
) -> None:
    await db.execute(
        update(models_feed.News)
        .where(
            models_feed.News.module == module,
            models_feed.News.module_object_id == module_object_id,
        )
        .values(**news_edit.model_dump(exclude_unset=True)),
    )


async def get_news_by_module_object_id(
    module: str,
    module_object_id: UUID,
    db: AsyncSession,
) -> models_feed.News | None:
    result = await db.execute(
        select(models_feed.News).where(
            models_feed.News.module == module,
            models_feed.News.module_object_id == module_object_id,
        ),
    )
    return result.scalars().first()


async def delete_news_by_module_object_id(
    module: str,
    module_object_id: UUID,
    db: AsyncSession,
) -> None:
    await db.execute(
        delete(models_feed.News).where(
            models_feed.News.module == module,
            models_feed.News.module_object_id == module_object_id,
        ),
    )
