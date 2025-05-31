from collections.abc import Sequence

from sqlalchemy import delete, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.advert import models_advert, schemas_advert


async def get_advertisers(db: AsyncSession) -> Sequence[models_advert.Advertiser]:
    result = await db.execute(select(models_advert.Advertiser))
    return result.scalars().all()


async def get_advertiser_by_id(
    db: AsyncSession,
    advertiser_id: str,
) -> models_advert.Advertiser | None:
    result = await db.execute(
        select(models_advert.Advertiser).where(
            models_advert.Advertiser.id == advertiser_id,
        ),
    )
    return result.scalars().first()


async def get_advertisers_by_groups(
    db: AsyncSession,
    user_groups_ids: Sequence[str],
) -> Sequence[models_advert.Advertiser] | None:
    result = await db.execute(
        select(models_advert.Advertiser).where(
            models_advert.Advertiser.group_manager_id.in_(user_groups_ids),
        ),
    )
    return result.scalars().all()


async def create_advertiser(
    db_advertiser: models_advert.Advertiser,
    db: AsyncSession,
) -> models_advert.Advertiser:
    db.add(db_advertiser)
    await db.flush()
    return db_advertiser


async def update_advertiser(
    advertiser_id: str,
    advertiser_update: schemas_advert.AdvertiserUpdate,
    db: AsyncSession,
):
    await db.execute(
        update(models_advert.Advertiser)
        .where(models_advert.Advertiser.id == advertiser_id)
        .values(**advertiser_update.model_dump(exclude_none=True)),
    )
    await db.flush()


async def delete_advertiser(advertiser_id: str, db: AsyncSession):
    await db.execute(
        delete(models_advert.Advertiser).where(
            models_advert.Advertiser.id == advertiser_id,
        ),
    )
    await db.flush()


async def get_adverts(db: AsyncSession) -> Sequence[models_advert.Advert]:
    result = await db.execute(select(models_advert.Advert))
    return result.scalars().all()


async def get_advert_by_id(
    db: AsyncSession,
    advert_id: str,
) -> models_advert.Advert | None:
    result = await db.execute(
        select(models_advert.Advert).where(models_advert.Advert.id == advert_id),
    )
    return result.scalars().first()


async def get_adverts_by_advertisers(
    db: AsyncSession,
    advertisers: list[str],
) -> Sequence[models_advert.Advert]:
    result = await db.execute(
        select(models_advert.Advert).where(
            or_(
                *[
                    models_advert.Advert.advertiser.has(
                        models_advert.Advertiser.id == advertiser_id,
                    )
                    for advertiser_id in advertisers
                ],
            ),
        ),
    )
    return result.scalars().all()


async def create_advert(
    db_advert: models_advert.Advert,
    db: AsyncSession,
) -> models_advert.Advert:
    db.add(db_advert)
    await db.flush()
    return db_advert


async def update_advert(
    advert_id: str,
    advert_update: schemas_advert.AdvertUpdate,
    db: AsyncSession,
):
    await db.execute(
        update(models_advert.Advert)
        .where(models_advert.Advert.id == advert_id)
        .values(**advert_update.model_dump(exclude_none=True)),
    )
    await db.flush()


async def delete_advert(advert_id: str, db: AsyncSession):
    await db.execute(
        delete(models_advert.Advert).where(models_advert.Advert.id == advert_id),
    )
    await db.flush()
