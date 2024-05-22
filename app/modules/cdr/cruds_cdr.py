from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.cdr import models_cdr, schemas_cdr


async def get_sellers(
    db: AsyncSession,
) -> Sequence[models_cdr.Seller]:
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


async def get_products(
    db: AsyncSession,
) -> Sequence[models_cdr.CdrProduct]:
    result = await db.execute(
        select(models_cdr.CdrProduct),
    )
    return result.scalars().all()


async def get_products_by_seller_id(
    db: AsyncSession,
    seller_id: UUID,
) -> Sequence[models_cdr.CdrProduct]:
    result = await db.execute(
        select(models_cdr.CdrProduct).where(
            models_cdr.CdrProduct.seller_id == seller_id,
        ),
    )
    return result.scalars().all()


async def get_available_online_products(
    db: AsyncSession,
) -> Sequence[models_cdr.CdrProduct]:
    result = await db.execute(
        select(models_cdr.CdrProduct).where(models_cdr.CdrProduct.available_online),
    )
    return result.scalars().all()


async def get_product_by_id(
    db: AsyncSession,
    product_id: UUID,
) -> models_cdr.CdrProduct | None:
    result = await db.execute(
        select(models_cdr.CdrProduct).where(models_cdr.CdrProduct.id == product_id),
    )
    return result.scalars().first()


async def create_product(
    db: AsyncSession,
    product: models_cdr.CdrProduct,
):
    db.add(product)


async def update_product(
    db: AsyncSession,
    product_id: UUID,
    product: schemas_cdr.ProductEdit,
):
    await db.execute(
        update(models_cdr.CdrProduct)
        .where(models_cdr.CdrProduct.id == product_id)
        .values(**product.model_dump(exclude_none=True)),
    )


async def delete_product(
    db: AsyncSession,
    product_id: UUID,
):
    await db.execute(
        delete(models_cdr.CdrProduct).where(models_cdr.CdrProduct.id == product_id),
    )


async def create_product_constraint(
    db: AsyncSession,
    product_constraint: models_cdr.ProductConstraint,
):
    db.add(product_constraint)


async def create_document_constraint(
    db: AsyncSession,
    document_constraint: models_cdr.DocumentConstraint,
):
    db.add(document_constraint)


async def delete_product_constraint(
    db: AsyncSession,
    product_id: UUID,
    product_constraint_id: UUID,
):
    await db.execute(
        delete(models_cdr.ProductConstraint).where(
            models_cdr.ProductConstraint.product_id == product_id,
            models_cdr.ProductConstraint.product_constraint_id == product_constraint_id,
        ),
    )


async def delete_document_constraint(
    db: AsyncSession,
    product_id: UUID,
    document_id: UUID,
):
    await db.execute(
        delete(models_cdr.DocumentConstraint).where(
            models_cdr.DocumentConstraint.product_id == product_id,
            models_cdr.DocumentConstraint.document_id == document_id,
        ),
    )


async def get_document_by_id(
    db: AsyncSession,
    document_id: UUID,
) -> models_cdr.Document | None:
    result = await db.execute(
        select(models_cdr.Document).where(models_cdr.Document.id == document_id),
    )
    return result.scalars().first()
