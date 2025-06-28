import logging
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.feed import cruds_feed
from app.core.feed.models_feed import News
from app.core.feed.types_feed import NewsStatus
from app.core.groups.groups_type import GroupType
from app.core.users import models_users
from app.dependencies import (
    get_db,
    is_user_an_ecl_member,
    is_user_in,
)
from app.types.module import CoreModule

router = APIRouter(tags=["Feed"])

core_module = CoreModule(
    root="feed",
    tag="Feed",
    router=router,
)

hyperion_error_logger = logging.getLogger("hyperion.error")


@router.get(
    "/feed/news",
    response_model=list[News],
    status_code=200,
)
async def get_published_news(
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_an_ecl_member),
):
    """
    Return published news from the feed
    """

    return await cruds_feed.get_news(status=[NewsStatus.PUBLISHED], db=db)


@router.get(
    "/feed/admin/news",
    response_model=list[News],
    status_code=200,
)
async def get_admin_news(
    status: list[NewsStatus],
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_in(GroupType.feed_admin)),
):
    """
    Return news from the feed

    **This endpoint is only usable by feed administrators**
    """

    return await cruds_feed.get_news(status=status, db=db)


@router.post(
    "/feed/admin/news/{news_id}/approve",
    response_model=list[News],
    status_code=200,
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
    response_model=list[News],
    status_code=200,
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
