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


async def get_sellers_by_group_ids(
    db: AsyncSession,
    group_ids: list[UUID],
) -> Sequence[models_cdr.Seller]:
    result = await db.execute(
        select(models_cdr.Seller)
        .where(models_cdr.Seller.group_id.in_(group_ids))
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
    await db.execute(
        delete(models_cdr.ProductConstraint).where(
            models_cdr.ProductConstraint.product_id == product_id,
        ),
    )
    await db.execute(
        delete(models_cdr.DocumentConstraint).where(
            models_cdr.DocumentConstraint.product_id == product_id,
        ),
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


async def get_product_variants(
    db: AsyncSession,
    product_id: UUID,
) -> Sequence[models_cdr.ProductVariant]:
    result = await db.execute(
        select(models_cdr.ProductVariant).where(
            models_cdr.ProductVariant.product_id == product_id,
        ),
    )
    return result.scalars().all()


async def get_enabled_product_variants(
    db: AsyncSession,
    product_id: UUID,
) -> Sequence[models_cdr.ProductVariant]:
    result = await db.execute(
        select(models_cdr.ProductVariant).where(
            models_cdr.ProductVariant.product_id == product_id,
            models_cdr.ProductVariant.enabled,
        ),
    )
    return result.scalars().all()


async def get_product_variant_by_id(
    db: AsyncSession,
    variant_id: UUID,
) -> models_cdr.ProductVariant | None:
    result = await db.execute(
        select(models_cdr.ProductVariant).where(
            models_cdr.ProductVariant.id == variant_id,
        ),
    )
    return result.scalars().first()


async def create_product_variant(
    db: AsyncSession,
    product_variant: models_cdr.ProductVariant,
):
    db.add(product_variant)


async def update_product_variant(
    db: AsyncSession,
    variant_id: UUID,
    product_variant: schemas_cdr.ProductVariantEdit,
):
    await db.execute(
        update(models_cdr.ProductVariant)
        .where(models_cdr.ProductVariant.id == variant_id)
        .values(**product_variant.model_dump(exclude_none=True)),
    )


async def create_allowed_curriculum(
    db: AsyncSession,
    allowed_curriculum: models_cdr.AllowedCurriculum,
):
    db.add(allowed_curriculum)


async def delete_allowed_curriculum(
    db: AsyncSession,
    variant_id: UUID,
    curriculum_id: UUID,
):
    await db.execute(
        delete(models_cdr.AllowedCurriculum).where(
            models_cdr.AllowedCurriculum.product_variant_id == variant_id,
            models_cdr.AllowedCurriculum.curriculum_id == curriculum_id,
        ),
    )


async def delete_product_variant(
    db: AsyncSession,
    variant_id: UUID,
):
    await db.execute(
        delete(models_cdr.ProductVariant).where(
            models_cdr.ProductVariant.id == variant_id,
        ),
    )


async def get_documents(
    db: AsyncSession,
) -> Sequence[models_cdr.Document]:
    result = await db.execute(select(models_cdr.Document))
    return result.scalars().all()


async def get_document_by_id(
    db: AsyncSession,
    document_id: UUID,
) -> models_cdr.Document | None:
    result = await db.execute(
        select(models_cdr.Document).where(models_cdr.Document.id == document_id),
    )
    return result.scalars().first()


async def create_document(
    db: AsyncSession,
    document: models_cdr.Document,
):
    db.add(document)


async def get_document_constraints_by_document_id(
    db: AsyncSession,
    document_id: UUID,
) -> Sequence[models_cdr.DocumentConstraint]:
    result = await db.execute(
        select(models_cdr.DocumentConstraint).where(
            models_cdr.DocumentConstraint.document_id == document_id,
        ),
    )
    return result.scalars().all()


async def delete_document(
    db: AsyncSession,
    document_id: UUID,
):
    await db.execute(
        delete(models_cdr.Document).where(
            models_cdr.Document.id == document_id,
        ),
    )


async def get_purchases(
    db: AsyncSession,
) -> Sequence[models_cdr.Purchase]:
    result = await db.execute(select(models_cdr.Purchase))
    return result.scalars().all()


async def get_purchases_by_user_id(
    db: AsyncSession,
    user_id: UUID,
) -> Sequence[models_cdr.Purchase]:
    result = await db.execute(
        select(models_cdr.Purchase).where(models_cdr.Purchase.user_id == user_id),
    )
    return result.scalars().all()


async def get_purchase_by_id(
    db: AsyncSession,
    user_id: UUID,
    product_variant_id: UUID,
) -> models_cdr.Purchase | None:
    result = await db.execute(
        select(models_cdr.Purchase).where(
            models_cdr.Purchase.user_id == user_id,
            models_cdr.Purchase.product_variant_id == product_variant_id,
        ),
    )
    return result.scalars().first()


async def create_purchase(
    db: AsyncSession,
    purchase: models_cdr.Purchase,
):
    db.add(purchase)


async def update_purchase(
    db: AsyncSession,
    user_id: UUID,
    product_variant_id: UUID,
    purchase: schemas_cdr.PurchaseEdit,
):
    await db.execute(
        update(models_cdr.Purchase)
        .where(
            models_cdr.Purchase.user_id == user_id,
            models_cdr.Purchase.product_variant_id == product_variant_id,
        )
        .values(**purchase.model_dump(exclude_none=True)),
    )


async def delete_purchase(
    db: AsyncSession,
    user_id: UUID,
    product_variant_id: UUID,
):
    await db.execute(
        delete(models_cdr.Purchase).where(
            models_cdr.Purchase.user_id == user_id,
            models_cdr.Purchase.product_variant_id == product_variant_id,
        ),
    )


async def mark_purchase_as_paid(
    db: AsyncSession,
    user_id: UUID,
    product_variant_id: UUID,
    paid: bool,
):
    await db.execute(
        update(models_cdr.Purchase)
        .where(
            models_cdr.Purchase.user_id == user_id,
            models_cdr.Purchase.product_variant_id == product_variant_id,
        )
        .values(paid=paid),
    )


async def get_signatures(
    db: AsyncSession,
) -> Sequence[models_cdr.Signature]:
    result = await db.execute(select(models_cdr.Signature))
    return result.scalars().all()


async def get_signatures_by_user_id(
    db: AsyncSession,
    user_id: UUID,
) -> Sequence[models_cdr.Signature]:
    result = await db.execute(
        select(models_cdr.Signature).where(models_cdr.Signature.user_id == user_id),
    )
    return result.scalars().all()


async def get_signatures_by_document_id(
    db: AsyncSession,
    document_id: UUID,
) -> Sequence[models_cdr.Signature]:
    result = await db.execute(
        select(models_cdr.Signature).where(
            models_cdr.Signature.document_id == document_id,
        ),
    )
    return result.scalars().all()


async def get_signature_by_id(
    db: AsyncSession,
    user_id: UUID,
    document_id: UUID,
) -> models_cdr.Signature | None:
    result = await db.execute(
        select(models_cdr.Signature).where(
            models_cdr.Signature.user_id == user_id,
            models_cdr.Signature.document_id == document_id,
        ),
    )
    return result.scalars().first()


async def create_signature(
    db: AsyncSession,
    signature: models_cdr.Signature,
):
    db.add(signature)


async def delete_signature(
    db: AsyncSession,
    user_id: UUID,
    document_id: UUID,
):
    await db.execute(
        delete(models_cdr.Signature).where(
            models_cdr.Signature.user_id == user_id,
            models_cdr.Signature.document_id == document_id,
        ),
    )


async def get_curriculum_by_id(
    db: AsyncSession,
    curriculum_id: UUID,
) -> models_cdr.Curriculum | None:
    result = await db.execute(
        select(models_cdr.Curriculum).where(models_cdr.Curriculum.id == curriculum_id),
    )
    return result.scalars().first()
