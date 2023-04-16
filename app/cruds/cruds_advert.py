from sqlalchemy import and_, delete, select, update
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
        raise ValueError()
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
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise ValueError()


async def delete_advertiser(advertiser_id: str, db: AsyncSession):
    await db.execute(
        delete(models_advert.Advertiser).where(
            models_advert.Advertiser.id == advertiser_id
        )
    )
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise ValueError()


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


async def get_adverts_by_advertisers(
    db: AsyncSession, advertisers: list[str] = []
) -> list[models_advert.Advert]:
    result = await db.execute(
        select(models_advert.Advert).where(
            and_(
                True,
                *[
                    models_advert.Advert.advertiser.has(
                        models_advert.Advertiser.id == advertiser_id
                    )
                    for advertiser_id in advertisers
                ],
            )
        )
    )
    return result.scalars().all()


async def create_advert(
    advert: schemas_advert.AdvertComplete, db: AsyncSession
) -> models_advert.Advert:
    db_advert = models_advert.Advert(**advert.dict())
    db.add(db_advert)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise ValueError()
    return db_advert


async def update_advert(
    advert_id: str, advert_update: schemas_advert.AdvertUpdate, db: AsyncSession
):
    await db.execute(
        update(models_advert.Advert)
        .where(models_advert.Advert.id == advert_id)
        .values(**advert_update.dict(exclude_none=True))
    )
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise ValueError()


async def delete_advert(advert_id: str, db: AsyncSession):
    await db.execute(
        delete(models_advert.Advert).where(models_advert.Advert.id == advert_id)
    )
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise ValueError()


"""
async def get_tag(db: AsyncSession) -> list[models_advert.Tag]:
    result = await db.execute(select(models_advert.Tag))
    return result.scalars().all()


async def get_tag_by_id(db: AsyncSession, tag_id: str) -> models_advert.Tag | None:
    result = await db.execute(
        select(models_advert.Tag).where(models_advert.Tag.id == tag_id)
    )
    return result.scalars().first()


async def get_tag_by_name(db: AsyncSession, tag_name: str) -> models_advert.Tag | None:
    result = await db.execute(
        select(models_advert.Tag).where(models_advert.Tag.name == tag_name)
    )
    return result.scalars().first()


async def create_tag(tag: models_advert.Tag, db: AsyncSession) -> models_advert.Tag:
    db_tag = models_advert.Tag(**tag.dict())
    db.add(db_tag)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise ValueError()
    return db_tag


async def update_tag(
    tag_id: str, tag_update: schemas_advert.TagUpdate, db: AsyncSession
):
    await db.execute(
        update(models_advert.Tag)
        .where(models_advert.Tag.id == tag_id)
        .values(**tag_update.dict(exclude_none=True))
    )
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise ValueError()


async def delete_tag(tag_id: str, db: AsyncSession):
    await db.execute(delete(models_advert.Tag).where(models_advert.Tag.id == tag_id))
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise ValueError()
"""
