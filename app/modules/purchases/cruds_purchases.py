from collections.abc import Sequence
from datetime import UTC, date, datetime
from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.models_core import CoreAssociationMembership, CoreUser
from app.modules.purchases import models_purchases, schemas_purchases
from app.types.membership import AvailableAssociationMembership


async def get_purchases_users_curriculum(
    db: AsyncSession,
) -> Sequence[models_purchases.CurriculumMembership]:
    result = await db.execute(
        select(models_purchases.CurriculumMembership),
    )
    return result.scalars().all()


async def get_purchases_user_curriculum(
    db: AsyncSession,
    user_id: str,
) -> models_purchases.CurriculumMembership | None:
    result = await db.execute(
        select(models_purchases.CurriculumMembership).where(
            models_purchases.CurriculumMembership.user_id == user_id,
        ),
    )
    return result.scalars().first()


async def get_sellers(
    db: AsyncSession,
) -> Sequence[models_purchases.Seller]:
    result = await db.execute(
        select(models_purchases.Seller),
    )
    return result.scalars().all()


async def get_online_sellers(
    db: AsyncSession,
) -> Sequence[models_purchases.Seller]:
    online_products = await get_online_products(db=db)
    seller_ids = set(product.seller_id for product in online_products)
    result = await db.execute(
        select(models_purchases.Seller).where(
            models_purchases.Seller.id.in_(seller_ids),
        ),
    )
    return result.scalars().all()


async def get_online_products(
    db: AsyncSession,
) -> Sequence[models_purchases.PurchasesProduct]:
    result = await db.execute(
        select(models_purchases.PurchasesProduct).where(
            models_purchases.PurchasesProduct.available_online,
        ),
    )
    return result.unique().scalars().all()


async def get_products(
    db: AsyncSession,
) -> Sequence[models_purchases.PurchasesProduct]:
    result = await db.execute(
        select(models_purchases.PurchasesProduct),
    )
    return result.unique().scalars().all()


async def get_sellers_by_group_ids(
    db: AsyncSession,
    group_ids: list[str],
) -> Sequence[models_purchases.Seller]:
    result = await db.execute(
        select(models_purchases.Seller).where(
            models_purchases.Seller.group_id.in_(group_ids),
        ),
    )
    return result.scalars().all()


async def get_seller_by_id(
    db: AsyncSession,
    seller_id: UUID,
) -> models_purchases.Seller | None:
    result = await db.execute(
        select(models_purchases.Seller).where(models_purchases.Seller.id == seller_id),
    )
    return result.scalars().first()


def create_seller(
    db: AsyncSession,
    seller: models_purchases.Seller,
):
    db.add(seller)


async def update_seller(
    db: AsyncSession,
    seller_id: UUID,
    seller: schemas_purchases.SellerEdit,
):
    if not bool(seller.model_fields_set):
        return

    await db.execute(
        update(models_purchases.Seller)
        .where(models_purchases.Seller.id == seller_id)
        .values(**seller.model_dump(exclude_none=True)),
    )


async def delete_seller(
    db: AsyncSession,
    seller_id: UUID,
):
    await db.execute(
        delete(models_purchases.Seller).where(models_purchases.Seller.id == seller_id),
    )


async def get_products_by_seller_id(
    db: AsyncSession,
    seller_id: UUID,
) -> Sequence[models_purchases.PurchasesProduct]:
    result = await db.execute(
        select(models_purchases.PurchasesProduct).where(
            models_purchases.PurchasesProduct.seller_id == seller_id,
        ),
    )
    return result.unique().scalars().all()


async def get_online_products_by_seller_id(
    db: AsyncSession,
    seller_id: UUID,
) -> Sequence[models_purchases.PurchasesProduct]:
    result = await db.execute(
        select(models_purchases.PurchasesProduct).where(
            models_purchases.PurchasesProduct.seller_id == seller_id,
            models_purchases.PurchasesProduct.available_online,
        ),
    )
    return result.unique().scalars().all()


async def get_product_by_id(
    db: AsyncSession,
    product_id: UUID,
) -> models_purchases.PurchasesProduct | None:
    result = await db.execute(
        select(models_purchases.PurchasesProduct).where(
            models_purchases.PurchasesProduct.id == product_id,
        ),
    )
    return result.unique().scalars().first()


def create_product(
    db: AsyncSession,
    product: models_purchases.PurchasesProduct,
):
    db.add(product)


async def update_product(
    db: AsyncSession,
    product_id: UUID,
    product: schemas_purchases.ProductEdit,
):
    if not bool(
        product.model_fields_set - {"product_constraints", "document_constraints"},
    ):
        # If there isn't any field to update, we do nothing
        return

    await db.execute(
        update(models_purchases.PurchasesProduct)
        .where(models_purchases.PurchasesProduct.id == product_id)
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
    """
    Delete a product and its associated `ProductConstraint` and `DocumentConstraint`
    """
    await db.execute(
        delete(models_purchases.ProductConstraint).where(
            models_purchases.ProductConstraint.product_constraint_id == product_id,
        ),
    )
    await db.execute(
        delete(models_purchases.PurchasesProduct).where(
            models_purchases.PurchasesProduct.id == product_id,
        ),
    )
    await db.execute(
        delete(models_purchases.ProductConstraint).where(
            models_purchases.ProductConstraint.product_id == product_id,
        ),
    )
    await db.execute(
        delete(models_purchases.DocumentConstraint).where(
            models_purchases.DocumentConstraint.product_id == product_id,
        ),
    )
    await db.execute(
        delete(models_purchases.PurchasesTicketGenerator).where(
            models_purchases.PurchasesTicketGenerator.product_id == product_id,
        ),
    )


def create_product_constraint(
    db: AsyncSession,
    product_constraint: models_purchases.ProductConstraint,
):
    db.add(product_constraint)


def create_document_constraint(
    db: AsyncSession,
    document_constraint: models_purchases.DocumentConstraint,
):
    db.add(document_constraint)


async def delete_product_constraints(
    db: AsyncSession,
    product_id: UUID,
):
    await db.execute(
        delete(models_purchases.ProductConstraint).where(
            models_purchases.ProductConstraint.product_id == product_id,
        ),
    )


async def delete_document_constraints(
    db: AsyncSession,
    product_id: UUID,
):
    await db.execute(
        delete(models_purchases.DocumentConstraint).where(
            models_purchases.DocumentConstraint.product_id == product_id,
        ),
    )


async def get_product_variant_by_id(
    db: AsyncSession,
    variant_id: UUID,
) -> models_purchases.ProductVariant | None:
    result = await db.execute(
        select(models_purchases.ProductVariant).where(
            models_purchases.ProductVariant.id == variant_id,
        ),
    )
    return result.scalars().first()


async def get_product_variants(
    db: AsyncSession,
    product_id: UUID,
) -> Sequence[models_purchases.ProductVariant]:
    result = await db.execute(
        select(models_purchases.ProductVariant).where(
            models_purchases.ProductVariant.product_id == product_id,
        ),
    )
    return result.scalars().all()


def create_product_variant(
    db: AsyncSession,
    product_variant: models_purchases.ProductVariant,
):
    db.add(product_variant)


async def update_product_variant(
    db: AsyncSession,
    variant_id: UUID,
    product_variant: schemas_purchases.ProductVariantEdit,
):
    if not bool(
        product_variant.model_fields_set - {"allowed_curriculum"},
    ):
        return

    await db.execute(
        update(models_purchases.ProductVariant)
        .where(models_purchases.ProductVariant.id == variant_id)
        .values(
            **product_variant.model_dump(
                exclude_none=True,
                exclude={"allowed_curriculum"},
            ),
        ),
    )


def create_allowed_curriculum(
    db: AsyncSession,
    allowed_curriculum: models_purchases.AllowedCurriculum,
):
    db.add(allowed_curriculum)


async def delete_allowed_curriculums(
    db: AsyncSession,
    variant_id: UUID,
):
    await db.execute(
        delete(models_purchases.AllowedCurriculum).where(
            models_purchases.AllowedCurriculum.product_variant_id == variant_id,
        ),
    )


async def delete_product_variant(
    db: AsyncSession,
    variant_id: UUID,
):
    await db.execute(
        delete(models_purchases.ProductVariant).where(
            models_purchases.ProductVariant.id == variant_id,
        ),
    )


async def get_all_documents(db: AsyncSession) -> Sequence[models_purchases.Document]:
    result = await db.execute(select(models_purchases.Document))
    return result.scalars().all()


async def get_documents_by_seller_id(
    db: AsyncSession,
    seller_id: UUID,
) -> Sequence[models_purchases.Document]:
    result = await db.execute(
        select(models_purchases.Document).where(
            models_purchases.Document.seller_id == seller_id,
        ),
    )
    return result.scalars().all()


async def get_document_by_id(
    db: AsyncSession,
    document_id: UUID,
) -> models_purchases.Document | None:
    result = await db.execute(
        select(models_purchases.Document).where(
            models_purchases.Document.id == document_id,
        ),
    )
    return result.scalars().first()


def create_document(
    db: AsyncSession,
    document: models_purchases.Document,
):
    db.add(document)


async def get_document_constraints_by_document_id(
    db: AsyncSession,
    document_id: UUID,
) -> Sequence[models_purchases.DocumentConstraint]:
    result = await db.execute(
        select(models_purchases.DocumentConstraint).where(
            models_purchases.DocumentConstraint.document_id == document_id,
        ),
    )
    return result.scalars().all()


async def delete_document(
    db: AsyncSession,
    document_id: UUID,
):
    await db.execute(
        delete(models_purchases.Document).where(
            models_purchases.Document.id == document_id,
        ),
    )


async def get_all_purchases(db: AsyncSession) -> Sequence[models_purchases.Purchase]:
    result = await db.execute(select(models_purchases.Purchase))
    return result.scalars().all()


async def get_purchases_by_user_id(
    db: AsyncSession,
    user_id: str,
) -> Sequence[models_purchases.Purchase]:
    result = await db.execute(
        select(models_purchases.Purchase)
        .where(models_purchases.Purchase.user_id == user_id)
        .options(selectinload("*")),
    )
    return result.scalars().all()


async def get_unpaid_purchases_by_user_id(
    db: AsyncSession,
    user_id: str,
    purchase_ids: list[UUID],
) -> Sequence[models_purchases.Purchase]:
    if purchase_ids != []:
        result = await db.execute(
            select(models_purchases.Purchase)
            .where(models_purchases.Purchase.user_id == user_id)
            .where(models_purchases.Purchase.product_variant_id.in_(purchase_ids))
            .where(models_purchases.Purchase.paid.is_(False))
            .options(selectinload("*")),
        )
    else:
        result = await db.execute(
            select(models_purchases.Purchase)
            .where(models_purchases.Purchase.user_id == user_id)
            .where(models_purchases.Purchase.paid.is_(False))
            .options(selectinload("*")),
        )
    return result.scalars().all()


async def get_purchase_by_id(
    db: AsyncSession,
    user_id: str,
    product_variant_id: UUID,
) -> models_purchases.Purchase | None:
    result = await db.execute(
        select(models_purchases.Purchase).where(
            models_purchases.Purchase.user_id == user_id,
            models_purchases.Purchase.product_variant_id == product_variant_id,
        ),
    )
    return result.scalars().first()


async def get_purchases_by_ids(
    db: AsyncSession,
    user_id: str,
    product_variant_id: list[UUID],
) -> Sequence[models_purchases.Purchase]:
    result = await db.execute(
        select(models_purchases.Purchase).where(
            models_purchases.Purchase.user_id == user_id,
            models_purchases.Purchase.product_variant_id.in_(product_variant_id),
        ),
    )
    return result.scalars().all()


async def get_purchases_by_user_id_by_seller_id(
    db: AsyncSession,
    user_id: str,
    seller_id: UUID,
) -> Sequence[models_purchases.Purchase]:
    result = await db.execute(
        select(models_purchases.Purchase)
        .join(models_purchases.ProductVariant)
        .join(models_purchases.PurchasesProduct)
        .where(
            models_purchases.PurchasesProduct.seller_id == seller_id,
            models_purchases.Purchase.user_id == user_id,
        ),
    )
    return result.scalars().all()


def create_purchase(
    db: AsyncSession,
    purchase: models_purchases.Purchase,
):
    db.add(purchase)


async def update_purchase(
    db: AsyncSession,
    user_id: str,
    product_variant_id: UUID,
    purchase: schemas_purchases.PurchaseBase,
):
    await db.execute(
        update(models_purchases.Purchase)
        .where(
            models_purchases.Purchase.user_id == user_id,
            models_purchases.Purchase.product_variant_id == product_variant_id,
        )
        .values(**purchase.model_dump(exclude_none=True)),
    )


async def delete_purchase(
    db: AsyncSession,
    user_id: str,
    product_variant_id: UUID,
    product_id: UUID,
):
    fields = (
        (
            await db.execute(
                select(models_purchases.CustomDataField).where(
                    models_purchases.CustomDataField.product_id == product_id,
                ),
            )
        )
        .scalars()
        .all()
    )
    await db.execute(
        delete(models_purchases.CustomData).where(
            models_purchases.CustomData.user_id == user_id,
            models_purchases.CustomData.field_id.in_([field.id for field in fields]),
        ),
    )
    await db.execute(
        delete(models_purchases.Purchase).where(
            models_purchases.Purchase.user_id == user_id,
            models_purchases.Purchase.product_variant_id == product_variant_id,
        ),
    )


async def mark_purchase_as_validated(
    db: AsyncSession,
    user_id: str,
    product_variant_id: UUID,
    validated: bool,
):
    await db.execute(
        update(models_purchases.Purchase)
        .where(
            models_purchases.Purchase.user_id == user_id,
            models_purchases.Purchase.product_variant_id == product_variant_id,
        )
        .values(validated=validated),
    )


async def mark_purchase_as_paid(
    db: AsyncSession,
    user_id: str,
    product_variant_ids: list[UUID],
):
    await db.execute(
        update(models_purchases.Purchase)
        .where(
            models_purchases.Purchase.user_id == user_id,
            models_purchases.Purchase.product_variant_id.in_(product_variant_ids),
        )
        .values(paid=True),
    )


async def get_signatures_by_user_id(
    db: AsyncSession,
    user_id: str,
) -> Sequence[models_purchases.Signature]:
    result = await db.execute(
        select(models_purchases.Signature).where(
            models_purchases.Signature.user_id == user_id,
        ),
    )
    return result.scalars().all()


async def get_signatures_by_user_id_by_seller_id(
    db: AsyncSession,
    user_id: str,
    seller_id: UUID,
) -> Sequence[models_purchases.Signature]:
    result = await db.execute(
        select(models_purchases.Signature)
        .join(models_purchases.Document)
        .where(
            models_purchases.Document.seller_id == seller_id,
            models_purchases.Signature.user_id == user_id,
        ),
    )
    return result.scalars().all()


async def get_signature_by_id(
    db: AsyncSession,
    user_id: str,
    document_id: UUID,
) -> models_purchases.Signature | None:
    result = await db.execute(
        select(models_purchases.Signature).where(
            models_purchases.Signature.user_id == user_id,
            models_purchases.Signature.document_id == document_id,
        ),
    )
    return result.scalars().first()


def create_signature(
    db: AsyncSession,
    signature: models_purchases.Signature,
):
    db.add(signature)


async def delete_signature(
    db: AsyncSession,
    user_id: str,
    document_id: UUID,
):
    await db.execute(
        delete(models_purchases.Signature).where(
            models_purchases.Signature.user_id == user_id,
            models_purchases.Signature.document_id == document_id,
        ),
    )


async def get_curriculums(
    db: AsyncSession,
) -> Sequence[models_purchases.Curriculum]:
    result = await db.execute(select(models_purchases.Curriculum))
    return result.scalars().all()


async def get_curriculum_by_id(
    db: AsyncSession,
    curriculum_id: UUID,
) -> models_purchases.Curriculum | None:
    result = await db.execute(
        select(models_purchases.Curriculum).where(
            models_purchases.Curriculum.id == curriculum_id,
        ),
    )
    return result.scalars().first()


def create_curriculum(
    db: AsyncSession,
    curriculum: models_purchases.Curriculum,
):
    db.add(curriculum)


async def delete_curriculum(
    db: AsyncSession,
    curriculum_id: UUID,
):
    await db.execute(
        delete(models_purchases.AllowedCurriculum).where(
            models_purchases.AllowedCurriculum.curriculum_id == curriculum_id,
        ),
    )
    await db.execute(
        delete(models_purchases.CurriculumMembership).where(
            models_purchases.CurriculumMembership.curriculum_id == curriculum_id,
        ),
    )
    await db.execute(
        delete(models_purchases.Curriculum).where(
            models_purchases.Curriculum.id == curriculum_id,
        ),
    )


async def get_curriculum_by_user_id(
    db: AsyncSession,
    user_id: str,
) -> models_purchases.CurriculumMembership | None:
    result = await db.execute(
        select(models_purchases.CurriculumMembership).where(
            models_purchases.CurriculumMembership.user_id == user_id,
        ),
    )
    return result.scalars().first()


def create_curriculum_membership(
    db: AsyncSession,
    curriculum_membership: models_purchases.CurriculumMembership,
):
    db.add(curriculum_membership)


async def update_curriculum_membership(
    db: AsyncSession,
    user_id: str,
    curriculum_id: UUID,
):
    await db.execute(
        update(models_purchases.CurriculumMembership)
        .where(
            models_purchases.CurriculumMembership.user_id == user_id,
        )
        .values(curriculum_id=curriculum_id),
    )


async def delete_curriculum_membership(
    db: AsyncSession,
    user_id: str,
    curriculum_id: UUID,
):
    await db.execute(
        delete(models_purchases.CurriculumMembership).where(
            models_purchases.CurriculumMembership.user_id == user_id,
            models_purchases.CurriculumMembership.curriculum_id == curriculum_id,
        ),
    )


async def get_payments_by_user_id(
    db: AsyncSession,
    user_id: str,
) -> Sequence[models_purchases.Payment]:
    result = await db.execute(
        select(models_purchases.Payment).where(
            models_purchases.Payment.user_id == user_id,
        ),
    )
    return result.scalars().all()


async def get_payment_by_id(
    db: AsyncSession,
    payment_id: UUID,
) -> models_purchases.Payment | None:
    result = await db.execute(
        select(models_purchases.Payment).where(
            models_purchases.Payment.id == payment_id,
        ),
    )
    return result.scalars().first()


def create_payment(
    db: AsyncSession,
    payment: models_purchases.Payment,
):
    db.add(payment)


async def delete_payment(
    db: AsyncSession,
    payment_id: UUID,
):
    await db.execute(
        delete(models_purchases.Payment).where(
            models_purchases.Payment.id == payment_id,
        ),
    )


async def get_actual_memberships_by_user_id(
    db: AsyncSession,
    user_id: str,
) -> Sequence[CoreAssociationMembership]:
    result = await db.execute(
        select(CoreAssociationMembership).where(
            CoreAssociationMembership.user_id == user_id,
            CoreAssociationMembership.end_date > date(datetime.now(UTC).year, 9, 5),
        ),
    )
    return result.scalars().all()


async def get_membership_by_user_id_and_membership_name(
    db: AsyncSession,
    user_id: str,
    membership: AvailableAssociationMembership,
) -> CoreAssociationMembership | None:
    result = await db.execute(
        select(CoreAssociationMembership).where(
            CoreAssociationMembership.user_id == user_id
            and CoreAssociationMembership.membership == membership,
        ),
    )
    return result.scalars().first()


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


async def update_membership(
    db: AsyncSession,
    membership_id: UUID,
    membership: schemas_purchases.MembershipEdit,
):
    await db.execute(
        update(CoreAssociationMembership)
        .where(CoreAssociationMembership.id == membership_id)
        .values(**membership.model_dump(exclude_none=True)),
    )


def create_action(
    db: AsyncSession,
    action: models_purchases.PurchasesAction,
):
    db.add(action)


def create_checkout(
    db: AsyncSession,
    checkout: models_purchases.Checkout,
):
    db.add(checkout)


def link_purchase_to_checkout(
    db: AsyncSession,
    user_id: str,
    product_variant_id: UUID,
    checkout_id: UUID,
):
    db.add(
        models_purchases.CheckoutPaidProduct(
            user_id=user_id,
            product_variant_id=product_variant_id,
            checkout_id=checkout_id,
        ),
    )


async def get_checkout_by_checkout_id(
    checkout_id: UUID,
    db: AsyncSession,
) -> models_purchases.Checkout | None:
    checkout = await db.execute(
        select(models_purchases.Checkout).where(
            models_purchases.Checkout.checkout_id == checkout_id,
        ),
    )
    return checkout.scalars().first()


def create_customdata_field(
    db: AsyncSession,
    datafield: models_purchases.CustomDataField,
):
    db.add(datafield)


async def get_customdata_field(
    db: AsyncSession,
    field_id: UUID,
) -> models_purchases.CustomDataField | None:
    result = await db.execute(
        select(models_purchases.CustomDataField).where(
            models_purchases.CustomDataField.id == field_id,
        ),
    )
    return result.scalars().first()


async def delete_customdata_field(db: AsyncSession, field_id: UUID):
    await db.execute(
        delete(models_purchases.CustomDataField).where(
            models_purchases.CustomDataField.id == field_id,
        ),
    )


def create_customdata(db: AsyncSession, data: models_purchases.CustomData):
    db.add(data)


async def get_customdata(
    db: AsyncSession,
    field_id: UUID,
    user_id: str,
) -> models_purchases.CustomData | None:
    result = await db.execute(
        select(models_purchases.CustomData)
        .where(
            models_purchases.CustomData.field_id == field_id,
            models_purchases.CustomData.user_id == user_id,
        )
        .options(selectinload(models_purchases.CustomData.field)),
    )
    return result.scalars().first()


async def get_product_customdata_fields(
    db: AsyncSession,
    product_id: UUID,
) -> Sequence[models_purchases.CustomDataField]:
    result = await db.execute(
        select(models_purchases.CustomDataField).where(
            models_purchases.CustomDataField.product_id == product_id,
        ),
    )
    return result.scalars().all()


async def update_customdata(db: AsyncSession, field_id: UUID, user_id: str, value: str):
    await db.execute(
        update(models_purchases.CustomData)
        .where(
            models_purchases.CustomData.field_id == field_id,
            models_purchases.CustomData.user_id == user_id,
        )
        .values(value=value),
    )


async def get_customdata_by_user_id(
    db: AsyncSession,
    user_id: str,
) -> Sequence[models_purchases.CustomData]:
    result = await db.execute(
        select(models_purchases.CustomData).where(
            models_purchases.CustomData.user_id == user_id,
        ),
    )
    return result.scalars().all()


async def delete_customdata(db: AsyncSession, field_id: UUID, user_id: str):
    await db.execute(
        delete(models_purchases.CustomData).where(
            models_purchases.CustomData.field_id == field_id,
            models_purchases.CustomData.user_id == user_id,
        ),
    )


async def get_pending_validation_users(db: AsyncSession) -> Sequence[CoreUser]:
    result = await db.execute(
        select(models_purchases.Purchase).where(
            models_purchases.Purchase.validated.is_(False),
        ),
    )
    user_ids = set(purchase.user_id for purchase in result.scalars().all())
    result_users = await db.execute(select(CoreUser).where(CoreUser.id.in_(user_ids)))
    return result_users.scalars().all()


async def get_product_validated_purchases(
    db: AsyncSession,
    product_id: UUID,
) -> Sequence[models_purchases.Purchase]:
    variant = await get_product_variants(db=db, product_id=product_id)
    variant_ids = [v.id for v in variant]
    result = await db.execute(
        select(models_purchases.Purchase).where(
            models_purchases.Purchase.validated.is_(True),
            models_purchases.Purchase.product_variant_id.in_(variant_ids),
        ),
    )
    return result.scalars().all()


def link_ticket_generator(
    db: AsyncSession,
    product_id: UUID,
    ticket_generator_id: UUID,
):
    db.add(
        models_purchases.PurchasesTicketGenerator(
            product_id=product_id,
            generator_id=ticket_generator_id,
        ),
    )


async def unlink_ticket_generator(
    db: AsyncSession,
    product_id: UUID,
    ticket_generator_id: UUID,
):
    await db.execute(
        delete(models_purchases.PurchasesTicketGenerator).where(
            models_purchases.PurchasesTicketGenerator.product_id == product_id,
            models_purchases.PurchasesTicketGenerator.generator_id
            == ticket_generator_id,
        ),
    )
