from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.sport_competition import (
    cruds_sport_competition,
    schemas_sport_competition,
)


async def check_validation_consistency(
    user: schemas_sport_competition.CompetitionUser,
    edition: schemas_sport_competition.CompetitionEdition,
    db: AsyncSession,
):
    participant = await cruds_sport_competition.load_participant_by_user_id(
        user.user.id,
        edition.id,
        db,
    )
    if participant and not participant.is_license_valid:
        raise HTTPException(
            status_code=400,
            detail="Participant license is not valid",
        )
    sport = (
        await cruds_sport_competition.load_sport_by_id(participant.sport_id, db)
        if participant
        else None
    )
    if participant and sport is None:
        raise HTTPException(
            status_code=404,
            detail="Sport not found in the database",
        )
    school_sport_quota = (
        await cruds_sport_competition.load_sport_quota_by_ids(
            participant.school_id,
            participant.sport_id,
            edition.id,
            db,
        )
        if participant
        else None
    )
    school_general_quota = await cruds_sport_competition.load_school_general_quota(
        user.user.school_id,
        edition.id,
        db,
    )
    school_product_quotas = (
        await cruds_sport_competition.load_all_school_product_quotas(
            user.user.school_id,
            edition.id,
            db,
        )
    )
    purchases = await cruds_sport_competition.load_purchases_by_user_id(
        user.user.id,
        edition.id,
        db,
    )
    required_products = await cruds_sport_competition.load_required_products(
        edition.id,
        db,
    )
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
    if (
        not any(
            purchase.product_variant.product_id in required_product_ids
            for purchase in purchases
        )
        and required_product_ids
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
    if user.is_athlete and school_general_quota.athlete_quota is not None:
        nb_athlete = await cruds_sport_competition.count_validated_competition_users_by_school_id(
            user.user.school_id,
            edition.id,
            db,
            is_athlete=True,
        )
        if nb_athlete >= school_general_quota.athlete_quota:
            raise HTTPException(
                status_code=400,
                detail="Athlete quota reached",
            )
    if user.is_cameraman and school_general_quota.cameraman_quota is not None:
        nb_cameraman = await cruds_sport_competition.count_validated_competition_users_by_school_id(
            user.user.school_id,
            edition.id,
            db,
            is_cameraman=True,
        )
        if nb_cameraman >= school_general_quota.cameraman_quota:
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
        if nb_pompom >= school_general_quota.pompom_quota:
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
        if nb_fanfare >= school_general_quota.fanfare_quota:
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
            user.user.school_id,
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
    if user.is_cameraman and school_general_quota.athlete_cameraman_quota is not None:
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
    if user.is_pompom and school_general_quota.athlete_pompom_quota is not None:
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
    if user.is_fanfare and school_general_quota.athlete_fanfare_quota is not None:
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
        if nb_cameraman >= school_general_quota.non_athlete_cameraman_quota:
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
        if nb_pompom >= school_general_quota.non_athlete_pompom_quota:
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
        if nb_fanfare >= school_general_quota.non_athlete_fanfare_quota:
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
            if nb_purchased >= product_quota.quota:
                raise HTTPException(
                    status_code=400,
                    detail=f"Product '{purchase.product_variant.name}' quota reached",
                )
