from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models_core import CoreAssociationMembership
from app.modules.cdr import models_cdr, schemas_cdr


async def get_cdr_users_curriculum(
    db: AsyncSession,
) -> Sequence[models_cdr.CurriculumMembership]:
    result = await db.execute(
        select(models_cdr.CurriculumMembership),
    )
    return result.scalars().all()


async def get_cdr_user_curriculum(
    db: AsyncSession,
    user_id: str,
) -> models_cdr.CurriculumMembership | None:
    result = await db.execute(
        select(models_cdr.CurriculumMembership).where(
            models_cdr.CurriculumMembership.user_id == user_id
        ),
    )
    return result.scalars().first()


async def get_sellers(
    db: AsyncSession,
) -> Sequence[models_cdr.Seller]:
    result = await db.execute(
        select(models_cdr.Seller),
    )
    return result.scalars().all()


async def get_online_sellers(
    db: AsyncSession,
) -> Sequence[models_cdr.Seller]:
    online_products = await db.execute(
        select(models_cdr.CdrProduct).where(models_cdr.CdrProduct.available_online),
    )
    seller_ids = set(
        product.seller_id for product in online_products.unique().scalars().all()
    )
    result = await db.execute(
        select(models_cdr.Seller).where(models_cdr.Seller.id.in_(seller_ids)),
    )
    return result.scalars().all()


async def get_online_products(
    db: AsyncSession,
) -> Sequence[models_cdr.CdrProduct]:
    result = await db.execute(
        select(models_cdr.CdrProduct).where(models_cdr.CdrProduct.available_online),
    )
    return result.unique().scalars().all()


async def get_products(
    db: AsyncSession,
) -> Sequence[models_cdr.CdrProduct]:
    result = await db.execute(
        select(models_cdr.CdrProduct),
    )
    return result.unique().scalars().all()


async def get_sellers_by_group_ids(
    db: AsyncSession,
    group_ids: list[str],
) -> Sequence[models_cdr.Seller]:
    result = await db.execute(
        select(models_cdr.Seller).where(models_cdr.Seller.group_id.in_(group_ids)),
    )
    return result.scalars().all()


async def get_seller_by_id(
    db: AsyncSession,
    seller_id: UUID,
) -> models_cdr.Seller | None:
    result = await db.execute(
        select(models_cdr.Seller).where(models_cdr.Seller.id == seller_id),
    )
    return result.scalars().first()


def create_seller(
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


async def get_products_by_seller_id(
    db: AsyncSession,
    seller_id: UUID,
) -> Sequence[models_cdr.CdrProduct]:
    result = await db.execute(
        select(models_cdr.CdrProduct).where(
            models_cdr.CdrProduct.seller_id == seller_id,
        ),
    )
    return result.unique().scalars().all()


async def get_online_products_by_seller_id(
    db: AsyncSession,
    seller_id: UUID,
) -> Sequence[models_cdr.CdrProduct]:
    result = await db.execute(
        select(models_cdr.CdrProduct).where(
            models_cdr.CdrProduct.seller_id == seller_id,
            models_cdr.CdrProduct.available_online,
        ),
    )
    return result.unique().scalars().all()


async def get_product_by_id(
    db: AsyncSession,
    product_id: UUID,
) -> models_cdr.CdrProduct | None:
    result = await db.execute(
        select(models_cdr.CdrProduct).where(models_cdr.CdrProduct.id == product_id),
    )
    return result.unique().scalars().first()


def create_product(
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
        .values(
            **product.model_dump(
                exclude_none=True,
                exclude={"product_constraints", "document_constraints"},
            ),
        ),
    )


async def delete_product(
    db: AsyncSession,
    product_id: UUID,
):
    await db.execute(
        delete(models_cdr.ProductConstraint).where(
            models_cdr.ProductConstraint.product_constraint_id == product_id,
        ),
    )
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


def create_product_constraint(
    db: AsyncSession,
    product_constraint: models_cdr.ProductConstraint,
):
    db.add(product_constraint)


def create_document_constraint(
    db: AsyncSession,
    document_constraint: models_cdr.DocumentConstraint,
):
    db.add(document_constraint)


async def delete_product_constraints(
    db: AsyncSession,
    product_id: UUID,
):
    await db.execute(
        delete(models_cdr.ProductConstraint).where(
            models_cdr.ProductConstraint.product_id == product_id,
        ),
    )


async def delete_document_constraints(
    db: AsyncSession,
    product_id: UUID,
):
    await db.execute(
        delete(models_cdr.DocumentConstraint).where(
            models_cdr.DocumentConstraint.product_id == product_id,
        ),
    )


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


def create_product_variant(
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
        .values(
            **product_variant.model_dump(
                exclude_none=True,
                exclude={"allowed_curriculum"},
            ),
        ),
    )


def create_allowed_curriculum(
    db: AsyncSession,
    allowed_curriculum: models_cdr.AllowedCurriculum,
):
    db.add(allowed_curriculum)


async def delete_allowed_curriculums(
    db: AsyncSession,
    variant_id: UUID,
):
    await db.execute(
        delete(models_cdr.AllowedCurriculum).where(
            models_cdr.AllowedCurriculum.product_variant_id == variant_id,
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


async def get_documents_by_seller_id(
    db: AsyncSession,
    seller_id: UUID,
) -> Sequence[models_cdr.Document]:
    result = await db.execute(
        select(models_cdr.Document).where(models_cdr.Document.seller_id == seller_id),
    )
    return result.scalars().all()


async def get_document_by_id(
    db: AsyncSession,
    document_id: UUID,
) -> models_cdr.Document | None:
    result = await db.execute(
        select(models_cdr.Document).where(models_cdr.Document.id == document_id),
    )
    return result.scalars().first()


def create_document(
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


async def get_purchases_by_user_id(
    db: AsyncSession,
    user_id: str,
) -> Sequence[models_cdr.Purchase]:
    result = await db.execute(
        select(models_cdr.Purchase).where(models_cdr.Purchase.user_id == user_id),
    )
    return result.scalars().all()


async def get_purchase_by_id(
    db: AsyncSession,
    user_id: str,
    product_variant_id: UUID,
) -> models_cdr.Purchase | None:
    result = await db.execute(
        select(models_cdr.Purchase).where(
            models_cdr.Purchase.user_id == user_id,
            models_cdr.Purchase.product_variant_id == product_variant_id,
        ),
    )
    return result.scalars().first()


async def get_purchases_by_ids(
    db: AsyncSession,
    user_id: str,
    product_variant_id: list[UUID],
) -> Sequence[models_cdr.Purchase]:
    result = await db.execute(
        select(models_cdr.Purchase).where(
            models_cdr.Purchase.user_id == user_id,
            models_cdr.Purchase.product_variant_id.in_(product_variant_id),
        ),
    )
    return result.scalars().all()


async def get_purchases_by_user_id_by_seller_id(
    db: AsyncSession,
    user_id: str,
    seller_id: UUID,
) -> Sequence[models_cdr.Purchase]:
    result = await db.execute(
        select(models_cdr.Purchase)
        .join(models_cdr.ProductVariant)
        .join(models_cdr.CdrProduct)
        .where(
            models_cdr.CdrProduct.seller_id == seller_id,
            models_cdr.Purchase.user_id == user_id,
        ),
    )
    return result.scalars().all()


def create_purchase(
    db: AsyncSession,
    purchase: models_cdr.Purchase,
):
    db.add(purchase)


async def update_purchase(
    db: AsyncSession,
    user_id: str,
    product_variant_id: UUID,
    purchase: schemas_cdr.PurchaseBase,
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
    user_id: str,
    product_variant_id: UUID,
):
    await db.execute(
        delete(models_cdr.Purchase).where(
            models_cdr.Purchase.user_id == user_id,
            models_cdr.Purchase.product_variant_id == product_variant_id,
        ),
    )


async def mark_purchase_as_validated(
    db: AsyncSession,
    user_id: str,
    product_variant_id: UUID,
    validated: bool,
):
    await db.execute(
        update(models_cdr.Purchase)
        .where(
            models_cdr.Purchase.user_id == user_id,
            models_cdr.Purchase.product_variant_id == product_variant_id,
        )
        .values(validated=validated),
    )


async def get_signatures_by_user_id(
    db: AsyncSession,
    user_id: str,
) -> Sequence[models_cdr.Signature]:
    result = await db.execute(
        select(models_cdr.Signature).where(models_cdr.Signature.user_id == user_id),
    )
    return result.scalars().all()


async def get_signatures_by_user_id_by_seller_id(
    db: AsyncSession,
    user_id: str,
    seller_id: UUID,
) -> Sequence[models_cdr.Signature]:
    result = await db.execute(
        select(models_cdr.Signature)
        .join(models_cdr.Document)
        .where(
            models_cdr.Document.seller_id == seller_id,
            models_cdr.Signature.user_id == user_id,
        ),
    )
    return result.scalars().all()


async def get_signature_by_id(
    db: AsyncSession,
    user_id: str,
    document_id: UUID,
) -> models_cdr.Signature | None:
    result = await db.execute(
        select(models_cdr.Signature).where(
            models_cdr.Signature.user_id == user_id,
            models_cdr.Signature.document_id == document_id,
        ),
    )
    return result.scalars().first()


def create_signature(
    db: AsyncSession,
    signature: models_cdr.Signature,
):
    db.add(signature)


async def delete_signature(
    db: AsyncSession,
    user_id: str,
    document_id: UUID,
):
    await db.execute(
        delete(models_cdr.Signature).where(
            models_cdr.Signature.user_id == user_id,
            models_cdr.Signature.document_id == document_id,
        ),
    )


async def get_curriculums(
    db: AsyncSession,
) -> Sequence[models_cdr.Curriculum]:
    result = await db.execute(select(models_cdr.Curriculum))
    return result.scalars().all()


async def get_curriculum_by_id(
    db: AsyncSession,
    curriculum_id: UUID,
) -> models_cdr.Curriculum | None:
    result = await db.execute(
        select(models_cdr.Curriculum).where(models_cdr.Curriculum.id == curriculum_id),
    )
    return result.scalars().first()


def create_curriculum(
    db: AsyncSession,
    curriculum: models_cdr.Curriculum,
):
    db.add(curriculum)


async def delete_curriculum(
    db: AsyncSession,
    curriculum_id: UUID,
):
    await db.execute(
        delete(models_cdr.AllowedCurriculum).where(
            models_cdr.AllowedCurriculum.curriculum_id == curriculum_id,
        ),
    )
    await db.execute(
        delete(models_cdr.CurriculumMembership).where(
            models_cdr.CurriculumMembership.curriculum_id == curriculum_id,
        ),
    )
    await db.execute(
        delete(models_cdr.Curriculum).where(
            models_cdr.Curriculum.id == curriculum_id,
        ),
    )


async def get_curriculum_by_user_id(
    db: AsyncSession,
    user_id: str,
) -> models_cdr.CurriculumMembership | None:
    result = await db.execute(
        select(models_cdr.CurriculumMembership).where(
            models_cdr.CurriculumMembership.user_id == user_id,
        ),
    )
    return result.scalars().first()


def create_curriculum_membership(
    db: AsyncSession,
    curriculum_membership: models_cdr.CurriculumMembership,
):
    db.add(curriculum_membership)


async def delete_curriculum_membership(
    db: AsyncSession,
    user_id: str,
    curriculum_id: UUID,
):
    await db.execute(
        delete(models_cdr.CurriculumMembership).where(
            models_cdr.CurriculumMembership.user_id == user_id,
            models_cdr.CurriculumMembership.curriculum_id == curriculum_id,
        ),
    )


async def get_payments_by_user_id(
    db: AsyncSession,
    user_id: str,
) -> Sequence[models_cdr.Payment]:
    result = await db.execute(
        select(models_cdr.Payment).where(models_cdr.Payment.user_id == user_id),
    )
    return result.scalars().all()


async def get_payment_by_id(
    db: AsyncSession,
    payment_id: UUID,
) -> models_cdr.Payment | None:
    result = await db.execute(
        select(models_cdr.Payment).where(models_cdr.Payment.id == payment_id),
    )
    return result.scalars().first()


def create_payment(
    db: AsyncSession,
    payment: models_cdr.Payment,
):
    db.add(payment)


async def delete_payment(
    db: AsyncSession,
    payment_id: UUID,
):
    await db.execute(
        delete(models_cdr.Payment).where(
            models_cdr.Payment.id == payment_id,
        ),
    )


async def get_memberships_by_user_id(
    db: AsyncSession,
    user_id: str,
) -> Sequence[CoreAssociationMembership]:
    result = await db.execute(
        select(CoreAssociationMembership).where(
            CoreAssociationMembership.user_id == user_id,
        ),
    )
    return result.scalars().all()


async def get_actual_memberships_by_user_id(
    db: AsyncSession,
    user_id: str,
) -> Sequence[CoreAssociationMembership]:
    result = await db.execute(
        select(CoreAssociationMembership).where(
            CoreAssociationMembership.user_id == user_id,
            CoreAssociationMembership.end_date > datetime.now(UTC).date(),
        ),
    )
    return result.scalars().all()


async def get_membership_by_id(
    db: AsyncSession,
    membership_id: UUID,
) -> CoreAssociationMembership | None:
    result = await db.execute(
        select(CoreAssociationMembership).where(
            CoreAssociationMembership.id == membership_id,
        ),
    )
    return result.scalars().first()


def create_membership(
    db: AsyncSession,
    membership: CoreAssociationMembership,
):
    db.add(membership)


async def delete_membership(
    db: AsyncSession,
    membership_id: UUID,
):
    await db.execute(
        delete(CoreAssociationMembership).where(
            CoreAssociationMembership.id == membership_id,
        ),
    )


def create_action(
    db: AsyncSession,
    action: models_cdr.CdrAction,
):
    db.add(action)
