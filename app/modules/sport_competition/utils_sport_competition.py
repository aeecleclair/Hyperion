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
    product_variant: schemas_sport_competition.ProductVariantWithProduct,
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
            == types_sport_competition.ProductPublicType.volunteer
            and not user.is_volunteer
        )
        or (
            product_variant.public_type
            == types_sport_competition.ProductPublicType.fanfare
            and not user.is_fanfare
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

    db_payment = schemas_sport_competition.PaymentComplete(
        id=uuid4(),
        user_id=checkout.user_id,
        total=paid_amount,
        edition_id=checkout.edition_id,
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

    purchases_total = sum(
        purchase.product_variant.price * purchase.quantity for purchase in purchases
    )
    payments_total = sum(payment.total for payment in payments)
    total_paid = payments_total + db_payment.total

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
    await cruds_sport_competition.add_payment(db_payment, db)
    await db.flush()


async def check_validation_consistency(
    user: schemas_sport_competition.CompetitionUser,
    participant: schemas_sport_competition.Participant | None,
    purchases: list[schemas_sport_competition.PurchaseComplete],
    school_sport_quota: schemas_sport_competition.SchoolSportQuota | None,
    school_general_quota: schemas_sport_competition.SchoolGeneralQuota | None,
    school_product_quotas: list[schemas_sport_competition.SchoolProductQuota],
    required_products: list[schemas_sport_competition.Product],
    edition: schemas_sport_competition.CompetitionEdition,
    db: AsyncSession,
):
    if participant and not user.is_athlete:
        raise HTTPException(
            status_code=400,
            detail="User is not an athlete but is registered as a participant",
        )
    if participant is None and user.is_athlete:
        raise HTTPException(
            status_code=400,
            detail="User is an athlete but is not registered as a participant",
        )
    required_product_ids = {product.id for product in required_products}
    if not any(
        purchase.product_variant.product_id in required_product_ids
        for purchase in purchases
    ):
        raise HTTPException(
            status_code=400,
            detail="User has not purchased the required products",
        )
    if school_sport_quota and participant:
        await check_participant_quotas(
            user,
            participant,
            school_sport_quota,
            edition,
            db,
        )
    if school_general_quota:
        await check_general_quotas(
            user,
            school_general_quota,
            edition,
            db,
        )
        if user.is_athlete:
            await check_athlete_quotas(
                user,
                school_general_quota,
                edition,
                db,
            )
        else:
            await check_non_athlete_quotas(
                user,
                school_general_quota,
                edition,
                db,
            )
    if school_product_quotas:
        await check_product_quotas(
            user,
            school_product_quotas,
            purchases,
            db,
        )


async def check_general_quotas(
    user: schemas_sport_competition.CompetitionUser,
    school_general_quota: schemas_sport_competition.SchoolGeneralQuota,
    edition: schemas_sport_competition.CompetitionEdition,
    db: AsyncSession,
):
    if user.is_cameraman and school_general_quota.cameraman_quota is not None:
        nb_cameraman = await cruds_sport_competition.count_validated_competition_users_by_school_id(
            user.user.school_id,
            edition.id,
            db,
            is_cameraman=True,
        )
        if nb_cameraman > school_general_quota.cameraman_quota:
            raise HTTPException(
                status_code=400,
                detail="Cameraman quota reached",
            )
    if user.is_pompom and school_general_quota.pompom_quota is not None:
        nb_pompom = await cruds_sport_competition.count_validated_competition_users_by_school_id(
            user.user.school_id,
            edition.id,
            db,
            is_pompom=True,
        )
        if nb_pompom > school_general_quota.pompom_quota:
            raise HTTPException(
                status_code=400,
                detail="Pompom quota reached",
            )
    if user.is_fanfare and school_general_quota.fanfare_quota is not None:
        nb_fanfare = await cruds_sport_competition.count_validated_competition_users_by_school_id(
            user.user.school_id,
            edition.id,
            db,
            is_fanfare=True,
        )
        if nb_fanfare > school_general_quota.fanfare_quota:
            raise HTTPException(
                status_code=400,
                detail="Fanfare quota reached",
            )


async def check_participant_quotas(
    user: schemas_sport_competition.CompetitionUser,
    participant: schemas_sport_competition.Participant,
    school_sport_quota: schemas_sport_competition.SchoolSportQuota,
    edition: schemas_sport_competition.CompetitionEdition,
    db: AsyncSession,
):
    if school_sport_quota.participant_quota is not None:
        nb_participants = await cruds_sport_competition.count_validated_participants_by_school_and_sport_ids(
            participant.school_id,
            participant.sport_id,
            edition.id,
            db,
        )
        if nb_participants >= school_sport_quota.participant_quota:
            raise HTTPException(
                status_code=400,
                detail="Participant quota reached",
            )


async def check_athlete_quotas(
    user: schemas_sport_competition.CompetitionUser,
    school_general_quota: schemas_sport_competition.SchoolGeneralQuota,
    edition: schemas_sport_competition.CompetitionEdition,
    db: AsyncSession,
):
    if user.is_cameraman and school_general_quota.athlete_cameraman_quota:
        nb_cameraman = await cruds_sport_competition.count_validated_competition_users_by_school_id(
            user.user.school_id,
            edition.id,
            db,
            is_athlete=True,
            is_cameraman=True,
        )
        if nb_cameraman >= school_general_quota.athlete_cameraman_quota:
            raise HTTPException(
                status_code=400,
                detail="Athlete cameraman quota reached",
            )
    if user.is_pompom and school_general_quota.athlete_pompom_quota:
        nb_pompom = await cruds_sport_competition.count_validated_competition_users_by_school_id(
            user.user.school_id,
            edition.id,
            db,
            is_athlete=True,
            is_pompom=True,
        )
        if nb_pompom >= school_general_quota.athlete_pompom_quota:
            raise HTTPException(
                status_code=400,
                detail="Athlete pompom quota reached",
            )
    if user.is_fanfare and school_general_quota.athlete_fanfare_quota:
        nb_fanfare = await cruds_sport_competition.count_validated_competition_users_by_school_id(
            user.user.school_id,
            edition.id,
            db,
            is_athlete=True,
            is_fanfare=True,
        )
        if nb_fanfare >= school_general_quota.athlete_fanfare_quota:
            raise HTTPException(
                status_code=400,
                detail="Athlete fanfare quota reached",
            )


async def check_non_athlete_quotas(
    user: schemas_sport_competition.CompetitionUser,
    school_general_quota: schemas_sport_competition.SchoolGeneralQuota,
    edition: schemas_sport_competition.CompetitionEdition,
    db: AsyncSession,
):
    if (
        user.is_cameraman
        and school_general_quota.non_athlete_cameraman_quota is not None
    ):
        nb_cameraman = await cruds_sport_competition.count_validated_competition_users_by_school_id(
            user.user.school_id,
            edition.id,
            db,
            is_athlete=False,
            is_cameraman=True,
        )
        if nb_cameraman > school_general_quota.non_athlete_cameraman_quota:
            raise HTTPException(
                status_code=400,
                detail="Non athlete cameraman quota reached",
            )
    if user.is_pompom and school_general_quota.non_athlete_pompom_quota is not None:
        nb_pompom = await cruds_sport_competition.count_validated_competition_users_by_school_id(
            user.user.school_id,
            edition.id,
            db,
            is_athlete=False,
            is_pompom=True,
        )
        if nb_pompom > school_general_quota.non_athlete_pompom_quota:
            raise HTTPException(
                status_code=400,
                detail="Non athlete pompom quota reached",
            )
    if user.is_fanfare and school_general_quota.non_athlete_fanfare_quota is not None:
        nb_fanfare = await cruds_sport_competition.count_validated_competition_users_by_school_id(
            user.user.school_id,
            edition.id,
            db,
            is_athlete=False,
            is_fanfare=True,
        )
        if nb_fanfare > school_general_quota.non_athlete_fanfare_quota:
            raise HTTPException(
                status_code=400,
                detail="Non athlete fanfare quota reached",
            )


async def check_product_quotas(
    user: schemas_sport_competition.CompetitionUser,
    school_product_quotas: list[schemas_sport_competition.SchoolProductQuota],
    purchases: list[schemas_sport_competition.PurchaseComplete],
    db: AsyncSession,
):
    for purchase in purchases:
        product_id = purchase.product_variant.product_id
        product_quota = next(
            (
                quota
                for quota in school_product_quotas
                if quota.product_id == product_id
            ),
            None,
        )
        if product_quota and product_quota.quota is not None:
            nb_purchased = await cruds_sport_competition.count_validated_purchases_by_product_id_and_school_id(
                user.user.school_id,
                product_id,
                db,
            )
            if nb_purchased > product_quota.quota:
                raise HTTPException(
                    status_code=400,
                    detail=f"Product {purchase.product_variant.product_id} quota reached",
                )
