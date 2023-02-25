from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import models_advert
from app.schemas import schemas_advert


async def get_advertisers(db: AsyncSession) -> list[models_advert.Advertiser]:
    result = await db.execute(select(models_advert.Advertiser))
    return result.scalars().all()


async def get_advertiser_by_id(
    db: AsyncSession, advertiser_id: str
) -> models_advert.Advertiser | None:
    result = await db.execute(
        select(models_advert.Advertiser).where(
            models_advert.Advertiser.id == advertiser_id
        )
    )
    return result.scalars().first()


async def create_advertiser(
    advertiser: schemas_advert.AdvertiserComplete, db: AsyncSession
) -> models_advert.Advertiser:
    db_advert = models_advert.Advertiser(**advertiser.dict())
    db.add(db_advert)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
    return db_advert


async def update_advertiser(
    advertiser_id: str,
    advertiser_update: schemas_advert.AdvertiserUpdate,
    db: AsyncSession,
):
    await db.execute(
        update(models_advert.Advertiser)
        .where(models_advert.Advertiser.id == advertiser_id)
        .values(**advertiser_update.dict(exclude_none=True))
    )
    await db.commit()


async def delete_advertiser(advertiser_id: str, db: AsyncSession):
    await db.execute(
        delete(models_advert.Advertiser).where(models_advert.Advertiser.id == advertiser_id)
    )
    await db.commit()


async def get_adverts(db: AsyncSession) -> list[models_advert.Advert]:
    result = await db.execute(select(models_advert.Advert))
    return result.scalars().all()


async def get_advert_by_id(
    db: AsyncSession, advert_id: str
) -> models_advert.Advert | None:
    result = await db.execute(
        select(models_advert.Advert).where(models_advert.Advert.id == advert_id)
    )
    return result.scalars().first()


async def create_advert(
    advert: schemas_advert.AdvertComplete, db: AsyncSession
) -> models_advert.Advert:
    db_advert = models_advert.Advert(**advert.dict())
    db.add(db_advert)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
    return db_advert


async def update_advert(
    advert_id: str, advert_update: schemas_advert.AdvertUpdate, db: AsyncSession
):
    await db.execute(
        update(models_advert.Advert)
        .where(models_advert.Advert.id == advert_id)
        .values(**advert_update.dict(exclude_none=True))
    )
    await db.commit()


async def delete_advert(advert_id: str, db: AsyncSession):
    await db.execute(
        delete(models_advert.Advert).where(models_advert.Advert.id == advert_id)
    )
    await db.commit()
