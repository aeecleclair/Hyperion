import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.feed import cruds_feed, schemas_feed
from app.core.feed.types_feed import NewsStatus
from app.core.groups.groups_type import GroupType
from app.core.users import models_users
from app.dependencies import (
    get_db,
    is_user_a_school_member,
    is_user_in,
)
from app.types.module import CoreModule
from app.utils.tools import get_file_from_data

router = APIRouter(tags=["Feed"])

core_module = CoreModule(
    root="feed",
    tag="Feed",
    router=router,
    factory=None,
)

hyperion_error_logger = logging.getLogger("hyperion.error")


@router.get(
    "/feed/news",
    response_model=list[schemas_feed.News],
    status_code=200,
)
async def get_published_news(
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_a_school_member),
):
    """
    Return published news from the feed
    """

    return await cruds_feed.get_news(status=[NewsStatus.PUBLISHED], db=db)


@router.get(
    "/feed/news/{news_id}/image",
    response_class=FileResponse,
    status_code=200,
)
async def get_news_image(
    news_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_a_school_member),
):
    """
    Return the image of a news
    """

    news = await cruds_feed.get_news_by_id(news_id=news_id, db=db)
    if news is None:
        raise HTTPException(
            status_code=404,
            detail="The news does not exist",
        )

    return get_file_from_data(
        directory=news.image_directory,
        filename=news.image_id,
    )


@router.get(
    "/feed/admin/news",
    response_model=list[schemas_feed.News],
    status_code=200,
)
async def get_admin_news(
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_in(GroupType.feed_admin)),
):
    """
    Return news from the feed

    **This endpoint is only usable by feed administrators**
    """

    return await cruds_feed.get_all_news(db=db)


@router.post(
    "/feed/admin/news/{news_id}/approve",
    status_code=204,
)
async def approve_news(
    news_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_in(GroupType.feed_admin)),
):
    """
    Approve a news

    **This endpoint is only usable by feed administrators**
    """

    return await cruds_feed.change_news_status(
        news_id=news_id,
        status=NewsStatus.PUBLISHED,
        db=db,
    )


@router.post(
    "/feed/admin/news/{news_id}/reject",
    status_code=204,
)
async def reject_news(
    news_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_in(GroupType.feed_admin)),
):
    """
    Reject a news

    **This endpoint is only usable by feed administrators**
    """

    await cruds_feed.change_news_status(
        news_id=news_id,
        status=NewsStatus.REJECTED,
        db=db,
    )
