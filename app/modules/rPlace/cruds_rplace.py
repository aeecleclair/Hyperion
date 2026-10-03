from datetime import UTC, datetime

from sqlalchemy import and_, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.rPlace import models_rplace


async def get_pixels(db: AsyncSession) -> list[models_rplace.Pixel]:
    subquery = (
        select(
            func.max(models_rplace.Pixel.date).label("max_date"),
            models_rplace.Pixel.x,
            models_rplace.Pixel.y,
        )
        .group_by(models_rplace.Pixel.x, models_rplace.Pixel.y)
        .alias("subquery")
    )

    result = await db.execute(
        select(models_rplace.Pixel)
        .join(
            subquery,
            and_(
                models_rplace.Pixel.x == subquery.c.x,
                models_rplace.Pixel.y == subquery.c.y,
                models_rplace.Pixel.date == subquery.c.max_date,
            ),
        )
        .order_by(models_rplace.Pixel.date.desc()),
    )

    return list(result.scalars().all())


async def create_pixel(
    db: AsyncSession,
    rplace_pixel: models_rplace.Pixel,
) -> models_rplace.Pixel:
    """Add a pixel in database"""
    db.add(rplace_pixel)
    try:
        await db.commit()
    except IntegrityError as error:
        await db.rollback()
        raise ValueError(error)
    return rplace_pixel


async def get_pixel_info(
    db: AsyncSession,
    x: int,
    y: int,
) -> models_rplace.Pixel | None:
    result = await db.execute(
        select(models_rplace.Pixel)
        .where(models_rplace.Pixel.x == x, models_rplace.Pixel.y == y)
        .order_by(models_rplace.Pixel.date.desc())
        .options(
            selectinload(models_rplace.Pixel.user),
        ),
    )

    return result.scalars().first()


async def get_last_pixel_date(
    db: AsyncSession,
    user_id: str,
) -> datetime:
    result = await db.execute(
        select(models_rplace.Pixel.date)
        .where(
            models_rplace.Pixel.user_id == user_id,
        )
        .order_by(
            models_rplace.Pixel.date.desc(),
        )
        .limit(1),
    )
    return result.scalars().first() or datetime(2003, 12, 18, 7, 46, 0, 0, UTC)
    #    return {"last_pixel_date": date_result.isoformat()}


async def get_last_pixel(
    db: AsyncSession,
    user_id: str,
) -> models_rplace.Pixel | None:
    result = await db.execute(
        select(models_rplace.Pixel)
        .where(
            models_rplace.Pixel.user_id == user_id,
        )
        .order_by(
            models_rplace.Pixel.date.desc(),
        ),
    )
    return result.scalars().first()
