from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.cdr import models_cdr, schemas_cdr


async def get_sellers(
    db: AsyncSession,
) -> Sequence[models_cdr.Seller]:
    """Return papers from the latest to the oldest"""
    result = await db.execute(
        select(models_cdr.Seller).options(selectinload(models_cdr.Seller.products)),
    )
    return result.scalars().all()


async def get_sellers_by_group_id(
    db: AsyncSession,
    group_id: UUID,
) -> Sequence[models_cdr.Seller]:
    result = await db.execute(
        select(models_cdr.Seller)
        .where(models_cdr.Seller.group_id == group_id)
        .options(selectinload(models_cdr.Seller.products)),
    )
    return result.scalars().all()


async def get_seller_by_id(
    db: AsyncSession,
    seller_id: UUID,
) -> models_cdr.Seller | None:
    result = await db.execute(
        select(models_cdr.Seller)
        .where(models_cdr.Seller.id == seller_id)
        .options(selectinload(models_cdr.Seller.products)),
    )
    return result.scalars().first()


async def create_seller(
    db: AsyncSession,
    seller: models_cdr.Seller,
):
    """Create a new seller in database"""
    db.add(seller)


async def update_seller(
    db: AsyncSession,
    seller_id: UUID,
    seller: schemas_cdr.SellerEdit,
):
    await db.execute(
        update(models_cdr.Seller)
        .where(models_cdr.Seller.id == seller_id)
        .values(**seller.model_dump(exclude_none=True)),
    )


async def delete_seller(
    db: AsyncSession,
    seller_id: UUID,
):
    await db.execute(
        delete(models_cdr.Seller).where(models_cdr.Seller.id == seller_id),
    )
