import logging
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.payment import schemas_payment
from app.core.schools.schools_type import SchoolType
from app.modules.sport_competition import (
    cruds_sport_competition,
    schemas_sport_competition,
    types_sport_competition,
)

hyperion_error_logger = logging.getLogger("hyperion.error")


def checksport_category_compatibility(
    sport_category1: types_sport_competition.SportCategory | None,
    sport_category2: types_sport_competition.SportCategory | None,
):
    """
    Check if two sport categories are compatible.
    If one of the categories is None, they are compatible.
    If both categories are the same, they are compatible.
    If both categories are different, they are not compatible.
    """
    if sport_category1 is None or sport_category2 is None:
        return True
    return sport_category1 == sport_category2


def get_public_type_from_user(
    user: schemas_sport_competition.CompetitionUser,
) -> list[types_sport_competition.ProductPublicType]:
    types = []
    if user.is_athlete:
        types.append(types_sport_competition.ProductPublicType.athlete)
    elif user.is_pompom:
        types.append(types_sport_competition.ProductPublicType.pompom)
    elif user.is_cameraman:
        types.append(types_sport_competition.ProductPublicType.cameraman)
    elif user.is_fanfare:
        types.append(types_sport_competition.ProductPublicType.fanfare)
    if user.is_volunteer:
        types.append(types_sport_competition.ProductPublicType.volunteer)
    return types


def validate_product_variant_purchase(
    purchase: schemas_sport_competition.PurchaseBase,
    product_variant: schemas_sport_competition.ProductVariantComplete,
    user: schemas_sport_competition.CompetitionUser,
    user_school: schemas_sport_competition.SchoolExtension,
    edition: schemas_sport_competition.CompetitionEdition,
) -> None:
    if purchase.quantity < 1:
        raise HTTPException(
            status_code=400,
            detail="Quantity must be at least 1",
        )
    if product_variant.product.edition_id != edition.id:
        raise HTTPException(
            status_code=403,
            detail="Product variant does not belong to the current edition",
        )
    if not product_variant.enabled:
        raise HTTPException(
            status_code=403,
            detail="This product variant is not available for purchase",
        )
    if product_variant.unique and purchase.quantity > 1:
        raise HTTPException(
            status_code=403,
            detail="You can only purchase one of this product variant",
        )
    if (
        (
            product_variant.school_type
            == types_sport_competition.ProductSchoolType.centrale
            and user.user.school_id != SchoolType.centrale_lyon.value
        )
        or (
            product_variant.school_type
            == types_sport_competition.ProductSchoolType.from_lyon
            and user_school.from_lyon is False
        )
        or (
            product_variant.school_type
            == types_sport_competition.ProductSchoolType.others
            and user_school.from_lyon is True
        )
        or (
            product_variant.public_type
            == types_sport_competition.ProductPublicType.athlete
            and not user.is_athlete
        )
        or (
            product_variant.public_type
            == types_sport_competition.ProductPublicType.cameraman
            and not user.is_cameraman
        )
        or (
            product_variant.public_type
            == types_sport_competition.ProductPublicType.pompom
            and not user.is_pompom
        )
        or (
            product_variant.public_type
            == types_sport_competition.ProductPublicType.fanfare
            and not user.is_fanfare
        )
        or (
            product_variant.public_type
            == types_sport_competition.ProductPublicType.volunteer
            and not user.is_volunteer
        )
    ):
        raise HTTPException(
            status_code=403,
            detail="You are not allowed to purchase this product variant",
        )


async def validate_payment(
    checkout_payment: schemas_payment.CheckoutPayment,
    db: AsyncSession,
) -> None:
    paid_amount = checkout_payment.paid_amount
    checkout_id = checkout_payment.checkout_id

    checkout = await cruds_sport_competition.get_checkout_by_checkout_id(
        checkout_id,
        db,
    )
    if not checkout:
        hyperion_error_logger.error(
            f"Competition payment callback: user checkout {checkout_id} not found.",
        )
        raise ValueError(f"User checkout {checkout_id} not found.")  # noqa: TRY003

    edition = await cruds_sport_competition.load_edition_by_id(
        checkout.edition_id,
        db,
    )
    if not edition or not edition.inscription_enabled:
        raise HTTPException(
            status_code=403,
            detail="Inscriptions are not enabled for this edition.",
        )

    db_payment = schemas_sport_competition.PaymentComplete(
        id=uuid4(),
        user_id=checkout.user_id,
        total=paid_amount,
        edition_id=checkout.edition_id,
        method=types_sport_competition.PaiementMethodType.helloasso,
    )
    purchases = await cruds_sport_competition.load_purchases_by_user_id(
        checkout.user_id,
        checkout.edition_id,
        db,
    )
    payments = await cruds_sport_competition.load_user_payments(
        checkout.user_id,
        checkout.edition_id,
        db,
    )

    await validate_purchases(purchases, [*payments, db_payment], db)
    await cruds_sport_competition.add_payment(db_payment, db)
    await db.flush()


async def validate_purchases(
    purchases: list[schemas_sport_competition.PurchaseComplete],
    payments: list[schemas_sport_competition.PaymentComplete],
    db: AsyncSession,
) -> None:
    if not purchases or len(purchases) == 0:
        raise HTTPException(
            status_code=400,
            detail="At least one purchase must be provided",
        )
    purchases_total = sum(
        purchase.product_variant.price * purchase.quantity for purchase in purchases
    )
    payments_total = sum(payment.total for payment in payments)
    total_paid = payments_total

    if total_paid == purchases_total:
        for purchase in purchases:
            await cruds_sport_competition.mark_purchase_as_validated(
                purchase.user_id,
                purchase.product_variant_id,
                True,
                db,
            )
    else:
        purchases.sort(key=lambda x: x.purchased_on)
        for purchase in purchases:
            if total_paid <= 0:
                break
            if purchase.validated:
                total_paid -= purchase.product_variant.price * purchase.quantity
                continue
            if purchase.product_variant.price * purchase.quantity <= total_paid:
                await cruds_sport_competition.mark_purchase_as_validated(
                    purchase.user_id,
                    purchase.product_variant_id,
                    True,
                    db,
                )
                total_paid -= purchase.product_variant.price * purchase.quantity
