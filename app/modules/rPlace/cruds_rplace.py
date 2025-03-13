from datetime import datetime

from sqlalchemy import delete, select, update, and_, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.rPlace import models_rplace

async def get_pixels(db: AsyncSession) -> list[models_rplace.Pixel]:
    subquery = (
        select(
            func.max(models_rplace.Pixel.date).label("max_date"),
            models_rplace.Pixel.x, models_rplace.Pixel.y
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
        .order_by(models_rplace.Pixel.date.desc())
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
        return rplace_pixel
    except IntegrityError as error:
        await db.rollback()
        raise ValueError(error)


async def get_pixel_info(db: AsyncSession, x: int, y: int) -> models_rplace.Pixel:
    result = await db.execute(
        select(models_rplace.Pixel)
        .where(models_rplace.Pixel.x == x, models_rplace.Pixel.y == y)
        .order_by(models_rplace.Pixel.date.desc())
    )

    return result.scalars().first()

