import logging
from datetime import UTC, datetime
from io import BytesIO
from uuid import UUID, uuid4

from fastapi import Body, Depends, File, HTTPException, Query, Response, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.groups.groups_type import get_account_types_except_externals
from app.core.payment.payment_tool import PaymentTool
from app.core.payment.types_payment import HelloAssoConfigName
from app.core.schools import cruds_schools
from app.core.schools.schools_type import SchoolType
from app.core.users import cruds_users, models_users, schemas_users
from app.dependencies import (
    get_db,
    get_payment_tool,
    is_user_allowed_to,
)
from app.modules.sport_competition import (
    cruds_sport_competition,
    schemas_sport_competition,
)
from app.modules.sport_competition.dependencies_sport_competition import (
    get_current_edition,
    has_user_competition_access,
    is_competition_user,
)
from app.modules.sport_competition.permissions_sport_competition import (
    SportCompetitionPermissions,
)
from app.modules.sport_competition.types_sport_competition import (
    CompetitionGroupType,
    ExcelExportParams,
    PaiementMethodType,
    ProductSchoolType,
    SportCategory,
)
from app.modules.sport_competition.utils.data_exporter.captain_exporter import (
    construct_captains_excel,
)
from app.modules.sport_competition.utils.data_exporter.global_exporter import (
    construct_users_excel_with_parameters,
)
from app.modules.sport_competition.utils.data_exporter.school_participants_exporter import (
    construct_school_users_excel_with_parameters,
)
from app.modules.sport_competition.utils.data_exporter.school_quotas_exporter import (
    construct_school_quotas_excel,
)
from app.modules.sport_competition.utils.data_exporter.sport_participants_exporter import (
    construct_sport_users_excel,
)
from app.modules.sport_competition.utils.data_exporter.sport_quotas_exporter import (
    construct_sport_quotas_excel,
)
from app.modules.sport_competition.utils.validation_checker import (
    check_validation_consistency,
)
from app.modules.sport_competition.utils_sport_competition import (
    checksport_category_compatibility,
    get_public_type_from_user,
    validate_payment,
    validate_product_variant_purchase,
    validate_purchases,
)
from app.types.content_type import ContentType
from app.types.module import Module
from app.utils.tools import (
    delete_file_from_data,
    get_file_from_data,
    has_user_permission,
    save_file_as_data,
)

hyperion_error_logger = logging.getLogger("hyperion.error")


module = Module(
    root="sport_competition",
    tag="Sport Competition",
    default_allowed_account_types=get_account_types_except_externals(),
    payment_callback=validate_payment,
    factory=None,
    permissions=SportCompetitionPermissions,
)

# region: Sport


@module.router.get(
    "/competition/sports",
    response_model=list[schemas_sport_competition.Sport],
)
async def get_sports(
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([SportCompetitionPermissions.access_sport_competition]),
    ),
) -> list[schemas_sport_competition.Sport]:
    return await cruds_sport_competition.load_all_sports(db)


@module.router.post(
    "/competition/sports",
    status_code=201,
    response_model=schemas_sport_competition.Sport,
)
async def create_sport(
    sport: schemas_sport_competition.SportBase,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([SportCompetitionPermissions.manage_sport_competition]),
    ),
) -> schemas_sport_competition.Sport:
    stored = await cruds_sport_competition.load_sport_by_name(sport.name, db)
    if stored is not None:
        raise HTTPException(
            status_code=400,
            detail="A sport with this name already exists",
        )
    sport = schemas_sport_competition.Sport(**sport.model_dump(), id=uuid4())
    await cruds_sport_competition.add_sport(sport, db)
    return sport


@module.router.patch(
    "/competition/sports/{sport_id}",
    status_code=204,
)
async def edit_sport(
    sport_id: UUID,
    sport: schemas_sport_competition.SportEdit,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([SportCompetitionPermissions.manage_sport_competition]),
    ),
) -> None:
    stored = await cruds_sport_competition.load_sport_by_id(sport_id, db)
    if stored is None:
        raise HTTPException(
            status_code=404,
            detail="Sport not found in the database",
        )
    if sport.name is not None:
        existing_sport = await cruds_sport_competition.load_sport_by_name(
            sport.name,
            db,
        )
        if existing_sport is not None and existing_sport.id != sport_id:
            raise HTTPException(
                status_code=400,
                detail="A sport with this name already exists",
            )
    await cruds_sport_competition.update_sport(
        sport_id,
        sport,
        db,
    )


@module.router.delete("/competition/sports/{sport_id}", status_code=204)
async def delete_sport(
    sport_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([SportCompetitionPermissions.manage_sport_competition]),
    ),
) -> None:
    stored = await cruds_sport_competition.load_sport_by_id(sport_id, db)
    if stored is None:
        raise HTTPException(
            status_code=404,
            detail="Sport not found in the database",
        )
    if stored.active:
        raise HTTPException(
            status_code=400,
            detail="Sport is activated and cannot be deleted",
        )
    await cruds_sport_competition.delete_sport_by_id(sport_id, db)


# endregion: Sport
# region: Edition


@module.router.get(
    "/competition/editions",
    response_model=list[schemas_sport_competition.CompetitionEdition],
)
async def get_editions(
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([SportCompetitionPermissions.access_sport_competition]),
    ),
) -> list[schemas_sport_competition.CompetitionEdition]:
    return await cruds_sport_competition.load_all_editions(db)


@module.router.get(
    "/competition/editions/active",
    response_model=schemas_sport_competition.CompetitionEdition | None,
)
async def get_active_edition(
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([SportCompetitionPermissions.access_sport_competition]),
    ),
) -> schemas_sport_competition.CompetitionEdition | None:
    """
    Get the currently active competition edition.
    Returns None if no edition is active.
    """
    return await cruds_sport_competition.load_active_edition(db)


@module.router.get(
    "/competition/editions/{edition_id}/stats",
    response_model=schemas_sport_competition.CompetitionEditionStats,
)
async def get_edition_stats(
    edition_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([SportCompetitionPermissions.manage_sport_competition]),
    ),
) -> schemas_sport_competition.CompetitionEditionStats:
    """
    Get the stats of a competition edition.
    """
    revenues_stats = await cruds_sport_competition.load_revenues_stats_by_edition_id(
        edition_id,
        db,
    )
    users_stats = (
        await cruds_sport_competition.load_competition_users_stats_by_edition_id(
            edition_id,
            db,
        )
    )
    sports_stats = await cruds_sport_competition.load_sports_stats_by_edition_id(
        edition_id,
        db,
    )
    return schemas_sport_competition.CompetitionEditionStats(
        revenues_stats=revenues_stats,
        users_stats=users_stats,
        sports_stats=sports_stats,
    )


@module.router.post(
    "/competition/editions",
    status_code=201,
    response_model=schemas_sport_competition.CompetitionEdition,
)
async def create_edition(
    edition: schemas_sport_competition.CompetitionEditionBase,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([SportCompetitionPermissions.manage_sport_competition]),
    ),
) -> schemas_sport_competition.CompetitionEdition:
    stored = await cruds_sport_competition.load_edition_by_name(edition.name, db)
    if stored is not None:
        raise HTTPException(
            status_code=400,
            detail="An edition with this name already exists",
        )
    edition = schemas_sport_competition.CompetitionEdition(
        **edition.model_dump(),
        id=uuid4(),
    )
    await cruds_sport_competition.add_edition(edition, db)
    return edition


@module.router.post(
    "/competition/editions/{edition_id}/activate",
    status_code=204,
)
async def activate_edition(
    edition_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([SportCompetitionPermissions.manage_sport_competition]),
    ),
) -> None:
    """
    Activate a competition edition.
    If another edition is already active, it will be deactivated.
    """
    stored = await cruds_sport_competition.load_edition_by_id(edition_id, db)
    if stored is None:
        raise HTTPException(
            status_code=404,
            detail="Edition not found in the database",
        )
    await cruds_sport_competition.set_active_edition(edition_id, db)


@module.router.post(
    "/competition/editions/{edition_id}/inscription",
    status_code=204,
)
async def enable_inscription(
    edition_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([SportCompetitionPermissions.manage_sport_competition]),
    ),
    enable: bool = Body(),
) -> None:
    """
    Enable inscription for a competition edition.
    The edition must already be active.
    """
    stored = await cruds_sport_competition.load_edition_by_id(edition_id, db)
    if stored is None:
        raise HTTPException(
            status_code=404,
            detail="Edition not found in the database",
        )
    if not stored.active:
        raise HTTPException(
            status_code=400,
            detail="Edition is not active, cannot patch inscription",
        )
    await cruds_sport_competition.patch_edition_inscription(edition_id, enable, db)


@module.router.patch(
    "/competition/editions/{edition_id}",
    status_code=204,
)
async def edit_edition(
    edition_id: UUID,
    edition_edit: schemas_sport_competition.CompetitionEditionEdit,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([SportCompetitionPermissions.manage_sport_competition]),
    ),
) -> None:
    stored = await cruds_sport_competition.load_edition_by_id(edition_id, db)
    if stored is None:
        raise HTTPException(
            status_code=404,
            detail="Edition not found in the database",
        )
    await cruds_sport_competition.update_edition(edition_id, edition_edit, db)


# endregion: Edition
# region: Competition User


@module.router.get(
    "/competition/users",
    response_model=list[schemas_sport_competition.CompetitionUser],
)
async def get_competition_users(
    db: AsyncSession = Depends(get_db),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([SportCompetitionPermissions.access_sport_competition]),
    ),
) -> list[schemas_sport_competition.CompetitionUser]:
    """
    Get all competition users for the current edition.
    """
    return await cruds_sport_competition.load_all_competition_users(edition.id, db)


@module.router.get(
    "/competition/users/schools/{school_id}",
    response_model=list[schemas_sport_competition.CompetitionUser],
)
async def get_competition_users_by_school(
    school_id: UUID,
    db: AsyncSession = Depends(get_db),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([SportCompetitionPermissions.access_sport_competition]),
    ),
) -> list[schemas_sport_competition.CompetitionUser]:
    """
    Get all competition users for the current edition by school.
    """
    return await cruds_sport_competition.load_all_competition_users_by_school(
        school_id,
        edition.id,
        db,
    )


@module.router.get(
    "/competition/users/me",
    response_model=schemas_sport_competition.CompetitionUser,
)
async def get_current_user_competition(
    db: AsyncSession = Depends(get_db),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([SportCompetitionPermissions.access_sport_competition]),
    ),
) -> schemas_sport_competition.CompetitionUser:
    """
    Get the competition user for the current edition.
    This is the user making the request.
    """
    competition_user = await cruds_sport_competition.load_competition_user_by_id(
        db=db,
        user_id=user.id,
        edition_id=edition.id,
    )
    if not competition_user:
        raise HTTPException(status_code=404, detail="User not found")
    return competition_user


@module.router.get(
    "/competition/users/{user_id}",
    response_model=schemas_sport_competition.CompetitionUser,
)
async def get_competition_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([SportCompetitionPermissions.manage_sport_competition]),
    ),
) -> schemas_sport_competition.CompetitionUser:
    """
    Get a competition user by their user ID for the current edition.
    """
    competition_user = await cruds_sport_competition.load_competition_user_by_id(
        db=db,
        user_id=user_id,
        edition_id=edition.id,
    )
    if not competition_user:
        raise HTTPException(status_code=404, detail="User not found")
    return competition_user


@module.router.post(
    "/competition/users",
    status_code=201,
    response_model=schemas_sport_competition.CompetitionUserSimple,
)
async def create_competition_user(
    competition_user: schemas_sport_competition.CompetitionUserBase,
    db: AsyncSession = Depends(get_db),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([SportCompetitionPermissions.access_sport_competition]),
    ),
) -> schemas_sport_competition.CompetitionUserSimple:
    """
    Create a competition user for the current edition.
    The user must exist in the core users database.
    """
    if not edition.inscription_enabled:
        raise HTTPException(
            status_code=400,
            detail="Inscriptions are not enabled for this edition",
        )
    school_extension = await cruds_sport_competition.load_school_base_by_id(
        user.school_id,
        db,
    )
    if school_extension is None or not school_extension.active:
        raise HTTPException(
            status_code=400,
            detail="Your school is not authorized to participate in the competition",
        )
    if not school_extension.inscription_enabled:
        raise HTTPException(
            status_code=400,
            detail="Inscriptions are not enabled for your school",
        )
    existing_competition_user = (
        await cruds_sport_competition.load_competition_user_by_id(
            db=db,
            user_id=user.id,
            edition_id=edition.id,
        )
    )
    if existing_competition_user is not None:
        raise HTTPException(
            status_code=400,
            detail="Competition user already exists",
        )
    user_simple = schemas_sport_competition.CompetitionUserSimple(
        user_id=user.id,
        edition_id=edition.id,
        is_athlete=competition_user.is_athlete,
        is_cameraman=competition_user.is_cameraman,
        is_pompom=competition_user.is_pompom,
        is_fanfare=competition_user.is_fanfare,
        sport_category=competition_user.sport_category,
        created_at=datetime.now(UTC),
        validated=False,
    )
    await cruds_sport_competition.add_competition_user(user_simple, db)
    return user_simple


@module.router.patch(
    "/competition/users/me",
    status_code=204,
)
async def edit_current_user_competition(
    user_edit: schemas_sport_competition.CompetitionUserEdit,
    db: AsyncSession = Depends(get_db),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
    user: schemas_users.CoreUser = Depends(
        is_user_allowed_to([SportCompetitionPermissions.access_sport_competition]),
    ),
) -> None:
    """
    Edit the current user's competition user for the current edition.
    The user must exist in the core users database.
    """
    if user_edit.validated:
        user_edit.validated = False
    stored = await cruds_sport_competition.load_competition_user_by_id(
        db=db,
        user_id=user.id,
        edition_id=edition.id,
    )
    if stored is None:
        raise HTTPException(
            status_code=404,
            detail="Competition user not found",
        )
    if stored.validated:
        user_edit.validated = False
    user_edit.is_athlete = (
        user_edit.is_athlete if user_edit.is_athlete is not None else stored.is_athlete
    )
    user_edit.is_cameraman = (
        user_edit.is_cameraman
        if user_edit.is_cameraman is not None
        else stored.is_cameraman
    )
    user_edit.is_pompom = (
        user_edit.is_pompom if user_edit.is_pompom is not None else stored.is_pompom
    )
    user_edit.is_fanfare = (
        user_edit.is_fanfare if user_edit.is_fanfare is not None else stored.is_fanfare
    )
    if (
        sum(
            [
                user_edit.is_pompom,
                user_edit.is_fanfare,
                user_edit.is_cameraman,
            ],
        )
        > 1
    ):
        raise HTTPException(
            status_code=400,
            detail="A user cannot be in more than one of the following categories: pompoms, fanfares, cameramen",
        )
    if not any(
        [
            user_edit.is_pompom,
            user_edit.is_fanfare,
            user_edit.is_cameraman,
            user_edit.is_athlete,
        ],
    ):
        raise HTTPException(
            status_code=400,
            detail="A user must be at least in one of the following categories: pompoms, fanfares, cameramen, athletes",
        )
    await cruds_sport_competition.update_competition_user(
        user.id,
        edition.id,
        user_edit,
        db,
    )


@module.router.patch(
    "/competition/users/{user_id}",
    status_code=204,
)
async def edit_competition_user(
    user_id: str,
    user_edit: schemas_sport_competition.CompetitionUserEdit,
    db: AsyncSession = Depends(get_db),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
    current_user: models_users.CoreUser = Depends(
        is_user_allowed_to([SportCompetitionPermissions.manage_sport_competition]),
    ),
) -> None:
    """
    Edit a competition user for the current edition.
    The user must exist in the core users database.
    """
    stored = await cruds_sport_competition.load_competition_user_by_id(
        db=db,
        user_id=user_id,
        edition_id=edition.id,
    )
    if stored is None:
        raise HTTPException(
            status_code=404,
            detail="Competition user not found",
        )
    if stored.validated:
        user_edit.validated = False
    user_edit.is_athlete = (
        user_edit.is_athlete if user_edit.is_athlete is not None else stored.is_athlete
    )
    user_edit.is_cameraman = (
        user_edit.is_cameraman
        if user_edit.is_cameraman is not None
        else stored.is_cameraman
    )
    user_edit.is_pompom = (
        user_edit.is_pompom if user_edit.is_pompom is not None else stored.is_pompom
    )
    user_edit.is_fanfare = (
        user_edit.is_fanfare if user_edit.is_fanfare is not None else stored.is_fanfare
    )
    if (
        sum(
            [
                user_edit.is_pompom,
                user_edit.is_fanfare,
                user_edit.is_cameraman,
            ],
        )
        > 1
    ):
        raise HTTPException(
            status_code=400,
            detail="A user cannot be in more than one of the following categories: pompoms, fanfares, cameramen",
        )
    if not any(
        [
            user_edit.is_pompom,
            user_edit.is_fanfare,
            user_edit.is_cameraman,
            user_edit.is_athlete,
        ],
    ):
        raise HTTPException(
            status_code=400,
            detail="A user must be at least in one of the following categories: pompoms, fanfares, cameramen, athletes",
        )
    await cruds_sport_competition.update_competition_user(
        user_id,
        edition.id,
        user_edit,
        db,
    )


@module.router.patch(
    "/competition/users/{user_id}/schools",
    status_code=204,
)
async def edit_user_school(
    user_id: str,
    school_id: UUID = Body(),
    db: AsyncSession = Depends(get_db),
    current_user: models_users.CoreUser = Depends(
        is_user_allowed_to([SportCompetitionPermissions.manage_sport_competition]),
    ),
) -> None:
    user = await cruds_users.get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(
            status_code=404,
            detail="User not found in the database",
        )
    if user.school_id != SchoolType.no_school.value:
        raise HTTPException(
            status_code=400,
            detail="User already has a school, cannot change it",
        )
    await cruds_users.update_user(
        db,
        user_id,
        schemas_users.CoreUserUpdateAdmin(school_id=school_id),
    )


@module.router.patch(
    "/competition/users/{user_id}/validate",
    status_code=204,
)
async def validate_competition_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        has_user_competition_access(
            competition_group=CompetitionGroupType.schools_bds,
        ),
    ),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
) -> None:
    if not edition.inscription_enabled:
        raise HTTPException(
            status_code=400,
            detail="Inscriptions are not enabled for this edition",
        )
    user_to_validate = await cruds_sport_competition.load_competition_user_by_id(
        user_id,
        edition.id,
        db,
    )
    if user_to_validate is None:
        raise HTTPException(
            status_code=404,
            detail="User not found in the database",
        )

    if (
        not (
            await has_user_permission(
                user,
                SportCompetitionPermissions.manage_sport_competition,
                db,
            )
        )
        and user.school_id != user_to_validate.user.school_id
    ):
        raise HTTPException(
            status_code=403,
            detail="Unauthorized action",
        )
    school_extension = await cruds_sport_competition.load_school_base_by_id(
        user_to_validate.user.school_id,
        db,
    )
    if school_extension is None or not school_extension.active:
        raise HTTPException(
            status_code=400,
            detail="The school of this user is not authorized to participate in the competition",
        )
    if not school_extension.inscription_enabled:
        raise HTTPException(
            status_code=400,
            detail="Inscriptions are not enabled for the school of this user",
        )

    await check_validation_consistency(
        user_to_validate,
        edition,
        db,
    )
    await cruds_sport_competition.validate_competition_user(
        user_id,
        edition.id,
        db,
    )


@module.router.patch(
    "/competition/users/{user_id}/cancel",
    status_code=204,
)
async def cancel_competition_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([SportCompetitionPermissions.manage_sport_competition]),
    ),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
) -> None:
    user_to_cancel = await cruds_sport_competition.load_competition_user_by_id(
        user_id,
        edition.id,
        db,
    )
    if user_to_cancel is None:
        raise HTTPException(
            status_code=404,
            detail="User not found in the database",
        )
    payments = await cruds_sport_competition.load_user_payments(
        user_id,
        edition.id,
        db,
    )
    if len(payments) == 0:
        raise HTTPException(
            status_code=400,
            detail="User has no payment, consider deleting the user instead of cancelling",
        )
    await cruds_sport_competition.delete_purchases_by_user_id(
        user_id,
        edition.id,
        db,
    )
    participant = await cruds_sport_competition.load_participant_by_user_id(
        user_id,
        edition.id,
        db,
    )
    if participant is not None:
        team = await cruds_sport_competition.load_team_by_id(
            participant.team_id,
            db,
        )
        if team is not None:
            if team.captain_id == user_id:
                next_user = next(
                    (user for user in team.participants if user.user_id != user_id),
                    None,
                )
                if next_user is not None:
                    await cruds_sport_competition.update_team(
                        team.id,
                        schemas_sport_competition.TeamEdit(
                            captain_id=next_user.user_id,
                        ),
                        db,
                    )
                else:
                    await cruds_sport_competition.delete_team_by_id(
                        team.id,
                        db,
                    )
        await cruds_sport_competition.delete_participant_by_user_id(
            user_id,
            edition.id,
            db,
        )
    await cruds_sport_competition.cancel_competition_user(
        user_id,
        edition.id,
        db,
    )


@module.router.patch(
    "/competition/users/{user_id}/invalidate",
    status_code=204,
)
async def invalidate_competition_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        has_user_competition_access(
            competition_group=CompetitionGroupType.schools_bds,
        ),
    ),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
) -> None:
    user_to_invalidate = await cruds_sport_competition.load_competition_user_by_id(
        user_id,
        edition.id,
        db,
    )
    if user_to_invalidate is None:
        raise HTTPException(
            status_code=404,
            detail="User not found in the database",
        )
    if not user_to_invalidate.validated:
        raise HTTPException(
            status_code=400,
            detail="User is not validated",
        )
    if (
        not (
            await has_user_permission(
                user,
                SportCompetitionPermissions.manage_sport_competition,
                db,
            )
        )
        and user.school_id != user_to_invalidate.user.school_id
    ):
        raise HTTPException(
            status_code=403,
            detail="Unauthorized action",
        )
    payments = await cruds_sport_competition.load_user_payments(
        user_id,
        edition.id,
        db,
    )
    if len(payments) > 0:
        raise HTTPException(
            status_code=400,
            detail="Cannot invalidate participant with payments",
        )
    await cruds_sport_competition.invalidate_competition_user(
        user_id,
        edition.id,
        db,
    )


@module.router.delete(
    "/competition/users/{user_id}",
    status_code=204,
)
async def delete_competition_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
    user: schemas_sport_competition.CompetitionUser = Depends(
        is_user_allowed_to([SportCompetitionPermissions.manage_sport_competition]),
    ),
) -> None:
    stored = await cruds_sport_competition.load_competition_user_by_id(
        db=db,
        user_id=user_id,
        edition_id=edition.id,
    )
    if stored is None:
        raise HTTPException(
            status_code=404,
            detail="Competition user not found",
        )
    if stored.validated:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete a validated competition user",
        )
    captain_team = await cruds_sport_competition.load_team_by_captain_id(
        user_id,
        edition.id,
        db,
    )
    if captain_team is not None:
        next_user = next(
            (user for user in captain_team.participants if user.user_id != user_id),
            None,
        )
        if next_user is None:
            await cruds_sport_competition.delete_team_by_id(
                captain_team.id,
                db,
            )
        else:
            await cruds_sport_competition.update_team(
                captain_team.id,
                schemas_sport_competition.TeamEdit(captain_id=next_user.user_id),
                db,
            )

    await cruds_sport_competition.delete_participant_by_user_id(
        user_id,
        edition.id,
        db,
    )
    await cruds_sport_competition.delete_purchases_by_user_id(
        user_id,
        edition.id,
        db,
    )
    await cruds_sport_competition.delete_competition_user_by_id(user_id, edition.id, db)


# endregion: Competition User
# region: Competition Groups


@module.router.get(
    "/competition/groups/{group}",
    response_model=list[schemas_sport_competition.UserGroupMembershipComplete],
)
async def get_group_members(
    group: CompetitionGroupType,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([SportCompetitionPermissions.manage_sport_competition]),
    ),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
) -> list[schemas_sport_competition.UserGroupMembershipComplete]:
    """
    Get all users in a specific competition group for the current edition.
    """
    return await cruds_sport_competition.load_memberships_by_competition_group(
        group,
        edition.id,
        db,
    )


@module.router.get(
    "/competition/users/me/groups",
    response_model=list[schemas_sport_competition.UserGroupMembership],
)
async def get_current_user_groups(
    db: AsyncSession = Depends(get_db),
    user: schemas_users.CoreUser = Depends(
        is_user_allowed_to([SportCompetitionPermissions.access_sport_competition]),
    ),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
) -> list[schemas_sport_competition.UserGroupMembership]:
    """
    Get all groups the current user is a member of in the current edition.
    This is the user making the request.
    """
    return await cruds_sport_competition.load_user_competition_groups_memberships(
        user.id,
        edition.id,
        db,
    )


@module.router.get(
    "/competition/users/{user_id}/groups",
    response_model=list[schemas_sport_competition.UserGroupMembership],
)
async def get_user_groups(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    user: schemas_users.CoreUser = Depends(
        is_user_allowed_to([SportCompetitionPermissions.manage_sport_competition]),
    ),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
) -> list[schemas_sport_competition.UserGroupMembership]:
    """
    Get all groups a user is a member of in the current edition.
    """
    user_to_check = await cruds_users.get_user_by_id(db, user_id)
    if user_to_check is None:
        raise HTTPException(
            status_code=404,
            detail="User not found in the database",
        )
    return await cruds_sport_competition.load_user_competition_groups_memberships(
        user_id,
        edition.id,
        db,
    )


@module.router.post(
    "/competition/groups/{group}/users/{user_id}",
    status_code=201,
    response_model=schemas_sport_competition.UserGroupMembership,
)
async def add_user_to_group(
    group: CompetitionGroupType,
    user_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([SportCompetitionPermissions.manage_sport_competition]),
    ),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
) -> schemas_sport_competition.UserGroupMembership:
    user_to_add = await cruds_users.get_user_by_id(db, user_id)
    if user_to_add is None:
        raise HTTPException(
            status_code=404,
            detail="User not found in the database",
        )
    membership = await cruds_sport_competition.load_user_competition_groups_memberships(
        user_id,
        edition.id,
        db,
    )
    if group in [m.group for m in membership]:
        raise HTTPException(
            status_code=400,
            detail="User is already a member of this group",
        )
    await cruds_sport_competition.add_user_to_group(user_id, group, edition.id, db)
    return schemas_sport_competition.UserGroupMembership(
        user_id=user_to_add.id,
        group=group,
        edition_id=edition.id,
    )


@module.router.delete(
    "/competition/groups/{group}/users/{user_id}",
    status_code=204,
)
async def remove_user_from_group(
    group: CompetitionGroupType,
    user_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([SportCompetitionPermissions.manage_sport_competition]),
    ),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
):
    membership = await cruds_sport_competition.load_user_competition_groups_memberships(
        user_id,
        edition.id,
        db,
    )
    if group not in [m.group for m in membership]:
        raise HTTPException(
            status_code=404,
            detail="User is not a member of this group",
        )
    await cruds_sport_competition.remove_user_from_group(
        user_id,
        group,
        edition.id,
        db,
    )


# endregion: Competition Groups
# region: Schools


@module.router.get(
    "/competition/schools",
    response_model=list[schemas_sport_competition.SchoolExtension],
)
async def get_schools(
    db: AsyncSession = Depends(get_db),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([SportCompetitionPermissions.access_sport_competition]),
    ),
) -> list[schemas_sport_competition.SchoolExtension]:
    return await cruds_sport_competition.load_all_schools(edition.id, db)


@module.router.get(
    "/competition/schools/{school_id}",
    response_model=schemas_sport_competition.SchoolExtension,
)
async def get_school(
    school_id: UUID,
    db: AsyncSession = Depends(get_db),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([SportCompetitionPermissions.access_sport_competition]),
    ),
) -> schemas_sport_competition.SchoolExtension:
    school = await cruds_sport_competition.load_school_by_id(school_id, db)
    if school is None:
        raise HTTPException(
            status_code=404,
            detail="School not found in the database",
        )
    return school


@module.router.post(
    "/competition/schools",
    status_code=201,
    response_model=schemas_sport_competition.SchoolExtensionBase,
)
async def create_school_extension(
    school: schemas_sport_competition.SchoolExtensionBase,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([SportCompetitionPermissions.manage_sport_competition]),
    ),
) -> schemas_sport_competition.SchoolExtensionBase:
    core_school = await cruds_schools.get_school_by_id(db, school.school_id)
    if core_school is None:
        raise HTTPException(
            status_code=404,
            detail="School not found in the database",
        )
    stored = await cruds_sport_competition.load_school_base_by_id(school.school_id, db)
    if stored is not None:
        raise HTTPException(
            status_code=400,
            detail="School extension already exists",
        )
    await cruds_sport_competition.add_school(school, db)
    return school


@module.router.patch(
    "/competition/schools/{school_id}",
    status_code=204,
)
async def edit_school_extension(
    school_id: UUID,
    school: schemas_sport_competition.SchoolExtensionEdit,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([SportCompetitionPermissions.manage_sport_competition]),
    ),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
) -> None:
    stored = await cruds_sport_competition.load_school_by_id(school_id, db)
    if stored is None:
        raise HTTPException(
            status_code=404,
            detail="School not found in the database",
        )
    await cruds_sport_competition.update_school(school_id, school, db)


@module.router.delete(
    "/competition/schools/{school_id}",
    status_code=204,
)
async def delete_school_extension(
    school_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([SportCompetitionPermissions.manage_sport_competition]),
    ),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
) -> None:
    stored = await cruds_sport_competition.load_school_by_id(school_id, db)
    if stored is None:
        raise HTTPException(
            status_code=404,
            detail="School not found in the database",
        )
    if stored.active:
        raise HTTPException(
            status_code=400,
            detail="School is activated and cannot be deleted",
        )
    await cruds_sport_competition.delete_school_by_id(school_id, db)


# endregion: Schools
# region: School General Quota


@module.router.get(
    "/competition/schools/{school_id}/general-quota",
    response_model=schemas_sport_competition.SchoolGeneralQuota,
)
async def get_school_general_quota(
    school_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        has_user_competition_access(
            competition_group=CompetitionGroupType.schools_bds,
        ),
    ),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
) -> schemas_sport_competition.SchoolGeneralQuota:
    school = await cruds_sport_competition.load_school_by_id(school_id, db)
    if school is None:
        raise HTTPException(
            status_code=404,
            detail="School not found in the database",
        )
    quota = await cruds_sport_competition.load_school_general_quota(
        school_id,
        edition.id,
        db,
    )
    if quota is None:
        raise HTTPException(
            status_code=404,
            detail="General quota not found for this school",
        )
    return quota


@module.router.post(
    "/competition/schools/{school_id}/general-quota",
    status_code=201,
    response_model=schemas_sport_competition.SchoolGeneralQuota,
)
async def create_school_general_quota(
    school_id: UUID,
    quota_info: schemas_sport_competition.SchoolGeneralQuotaBase,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([SportCompetitionPermissions.manage_sport_competition]),
    ),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
) -> schemas_sport_competition.SchoolGeneralQuota:
    school = await cruds_sport_competition.load_school_by_id(school_id, db)
    if school is None:
        raise HTTPException(
            status_code=404,
            detail="School not found in the database",
        )
    stored = await cruds_sport_competition.load_school_general_quota(
        school_id,
        edition.id,
        db,
    )
    if stored is not None:
        raise HTTPException(
            status_code=400,
            detail="General quota already exists for this school",
        )
    quota = schemas_sport_competition.SchoolGeneralQuota(
        school_id=school_id,
        edition_id=edition.id,
        athlete_quota=quota_info.athlete_quota,
        cameraman_quota=quota_info.cameraman_quota,
        pompom_quota=quota_info.pompom_quota,
        fanfare_quota=quota_info.fanfare_quota,
        athlete_cameraman_quota=quota_info.athlete_cameraman_quota,
        athlete_fanfare_quota=quota_info.athlete_fanfare_quota,
        athlete_pompom_quota=quota_info.athlete_pompom_quota,
        non_athlete_cameraman_quota=quota_info.non_athlete_cameraman_quota,
        non_athlete_fanfare_quota=quota_info.non_athlete_fanfare_quota,
        non_athlete_pompom_quota=quota_info.non_athlete_pompom_quota,
    )
    await cruds_sport_competition.add_school_general_quota(quota, db)
    return quota


@module.router.patch(
    "/competition/schools/{school_id}/general-quota",
    status_code=204,
)
async def edit_school_general_quota(
    school_id: UUID,
    quota_info: schemas_sport_competition.SchoolGeneralQuotaBase,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([SportCompetitionPermissions.manage_sport_competition]),
    ),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
) -> None:
    school = await cruds_sport_competition.load_school_by_id(school_id, db)
    if school is None:
        raise HTTPException(
            status_code=404,
            detail="School not found in the database",
        )
    stored = await cruds_sport_competition.load_school_general_quota(
        school_id,
        edition.id,
        db,
    )
    if stored is None:
        raise HTTPException(
            status_code=404,
            detail="General quota not found for this school",
        )
    await cruds_sport_competition.update_school_general_quota(
        school_id,
        edition.id,
        quota_info,
        db,
    )


# endregion: School General Quota
# region: Sport Quotas


@module.router.get(
    "/competition/sports/{sport_id}/quotas",
    response_model=list[schemas_sport_competition.SchoolSportQuota],
)
async def get_quotas_for_sport(
    sport_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([SportCompetitionPermissions.manage_sport_competition]),
    ),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
) -> list[schemas_sport_competition.SchoolSportQuota]:
    sport = await cruds_sport_competition.load_sport_by_id(sport_id, db)
    if sport is None:
        raise HTTPException(
            status_code=404,
            detail="Sport not found in the database",
        )
    return await cruds_sport_competition.load_all_sport_quotas_by_sport_id(
        sport_id,
        edition.id,
        db,
    )


@module.router.get(
    "/competition/schools/{school_id}/sports-quotas",
    response_model=list[schemas_sport_competition.SchoolSportQuota],
)
async def get_quotas_for_school(
    school_id: UUID,
    db: AsyncSession = Depends(get_db),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([SportCompetitionPermissions.access_sport_competition]),
    ),
) -> list[schemas_sport_competition.SchoolSportQuota]:
    school = await cruds_sport_competition.load_school_by_id(school_id, db)
    if school is None:
        raise HTTPException(
            status_code=404,
            detail="School not found in the database",
        )
    return await cruds_sport_competition.load_all_sport_quotas_by_school_id(
        school_id,
        edition.id,
        db,
    )


@module.router.post(
    "/competition/schools/{school_id}/sports/{sport_id}/quotas",
    status_code=204,
)
async def create_sport_quota(
    school_id: UUID,
    sport_id: UUID,
    quota_info: schemas_sport_competition.SportQuotaInfo,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([SportCompetitionPermissions.manage_sport_competition]),
    ),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
) -> None:
    school = await cruds_sport_competition.load_school_by_id(school_id, db)
    if school is None:
        raise HTTPException(
            status_code=404,
            detail="School not found in the database",
        )
    sport = await cruds_sport_competition.load_sport_by_id(sport_id, db)
    if sport is None:
        raise HTTPException(
            status_code=404,
            detail="Sport not found in the database",
        )
    stored = await cruds_sport_competition.load_sport_quota_by_ids(
        school_id,
        sport_id,
        edition.id,
        db,
    )
    if stored is not None:
        raise HTTPException(status_code=400, detail="Quota already exists")
    quota = schemas_sport_competition.SchoolSportQuota(
        school_id=school_id,
        sport_id=sport_id,
        participant_quota=quota_info.participant_quota,
        team_quota=quota_info.team_quota,
        edition_id=edition.id,
    )
    await cruds_sport_competition.add_sport_quota(quota, db)


@module.router.patch(
    "/competition/schools/{school_id}/sports/{sport_id}/quotas",
    status_code=204,
)
async def edit_sport_quota(
    school_id: UUID,
    sport_id: UUID,
    quota_info: schemas_sport_competition.SchoolSportQuotaEdit,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([SportCompetitionPermissions.manage_sport_competition]),
    ),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
) -> None:
    stored = await cruds_sport_competition.load_sport_quota_by_ids(
        school_id,
        sport_id,
        edition.id,
        db,
    )
    if stored is None:
        raise HTTPException(
            status_code=404,
            detail="Quota not found in the database",
        )
    await cruds_sport_competition.update_sport_quota(
        school_id,
        sport_id,
        edition.id,
        quota_info,
        db,
    )


@module.router.delete(
    "/competition/schools/{school_id}/sports/{sport_id}/quotas",
    status_code=204,
)
async def delete_sport_quota(
    school_id: UUID,
    sport_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([SportCompetitionPermissions.manage_sport_competition]),
    ),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
) -> None:
    stored = await cruds_sport_competition.load_sport_quota_by_ids(
        school_id,
        sport_id,
        edition.id,
        db,
    )
    if stored is None:
        raise HTTPException(
            status_code=404,
            detail="Quota not found in the database",
        )
    await cruds_sport_competition.delete_sport_quota_by_ids(
        school_id,
        sport_id,
        edition.id,
        db,
    )


# endregion: Sport Quotas
# region: Product Quotas


@module.router.get(
    "/competition/schools/{school_id}/product-quotas",
    response_model=list[schemas_sport_competition.SchoolProductQuota],
)
async def get_product_quotas_for_school(
    school_id: UUID,
    db: AsyncSession = Depends(get_db),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([SportCompetitionPermissions.access_sport_competition]),
    ),
) -> list[schemas_sport_competition.SchoolProductQuota]:
    school = await cruds_sport_competition.load_school_by_id(school_id, db)
    if school is None:
        raise HTTPException(
            status_code=404,
            detail="School not found in the database",
        )
    return await cruds_sport_competition.load_all_school_product_quotas(
        school_id,
        edition.id,
        db,
    )


@module.router.get(
    "/competition/products/{product_id}/schools-quotas",
    response_model=list[schemas_sport_competition.SchoolProductQuota],
)
async def get_product_quotas_for_product(
    product_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([SportCompetitionPermissions.manage_sport_competition]),
    ),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
) -> list[schemas_sport_competition.SchoolProductQuota]:
    product = await cruds_sport_competition.load_product_by_id(product_id, db)
    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found in the database",
        )
    return await cruds_sport_competition.load_all_product_quotas_by_product_id(
        product_id,
        db,
    )


@module.router.post(
    "/competition/schools/{school_id}/product-quotas",
    status_code=201,
    response_model=schemas_sport_competition.SchoolProductQuota,
)
async def create_product_quota(
    school_id: UUID,
    quota_info: schemas_sport_competition.SchoolProductQuotaBase,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([SportCompetitionPermissions.manage_sport_competition]),
    ),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
) -> schemas_sport_competition.SchoolProductQuota:
    school = await cruds_sport_competition.load_school_by_id(school_id, db)
    if school is None:
        raise HTTPException(
            status_code=404,
            detail="School not found in the database",
        )
    product = await cruds_sport_competition.load_product_by_id(
        quota_info.product_id,
        db,
    )
    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found in the database",
        )
    stored = await cruds_sport_competition.load_school_product_quota_by_ids(
        school_id,
        quota_info.product_id,
        db,
    )
    if stored is not None:
        raise HTTPException(status_code=400, detail="Quota already exists")
    quota = schemas_sport_competition.SchoolProductQuota(
        school_id=school_id,
        product_id=quota_info.product_id,
        quota=quota_info.quota,
        edition_id=edition.id,
    )
    await cruds_sport_competition.add_school_product_quota(quota, db)
    return quota


@module.router.patch(
    "/competition/schools/{school_id}/product-quotas/{product_id}",
    status_code=204,
)
async def edit_product_quota(
    school_id: UUID,
    product_id: UUID,
    quota_info: schemas_sport_competition.SchoolProductQuotaEdit,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([SportCompetitionPermissions.manage_sport_competition]),
    ),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
) -> None:
    stored = await cruds_sport_competition.load_school_product_quota_by_ids(
        school_id,
        product_id,
        db,
    )
    if stored is None:
        raise HTTPException(
            status_code=404,
            detail="Quota not found in the database",
        )
    await cruds_sport_competition.update_school_product_quota(
        school_id,
        product_id,
        quota_info,
        db,
    )


@module.router.delete(
    "/competition/schools/{school_id}/product-quotas/{product_id}",
    status_code=204,
)
async def delete_product_quota(
    school_id: UUID,
    product_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([SportCompetitionPermissions.manage_sport_competition]),
    ),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
) -> None:
    stored = await cruds_sport_competition.load_school_product_quota_by_ids(
        school_id,
        product_id,
        db,
    )
    if stored is None:
        raise HTTPException(
            status_code=404,
            detail="Quota not found in the database",
        )
    await cruds_sport_competition.delete_school_product_quota_by_ids(
        school_id,
        product_id,
        db,
    )


# endregion: Product Quotas
# region: Teams


@module.router.get(
    "/competition/teams",
    response_model=list[schemas_sport_competition.TeamComplete],
)
async def get_teams(
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([SportCompetitionPermissions.access_sport_competition]),
    ),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
) -> list[schemas_sport_competition.TeamComplete]:
    return await cruds_sport_competition.load_all_teams(edition.id, db)


@module.router.get(
    "/competition/teams/me",
    response_model=schemas_sport_competition.TeamComplete,
)
async def get_current_user_team_as_captain(
    db: AsyncSession = Depends(get_db),
    user: schemas_users.CoreUser = Depends(
        is_user_allowed_to([SportCompetitionPermissions.access_sport_competition]),
    ),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
) -> schemas_sport_competition.TeamComplete:
    team = await cruds_sport_competition.load_team_by_captain_id(
        user.id,
        edition.id,
        db,
    )
    if team is None:
        raise HTTPException(
            status_code=404,
            detail="Team not found for the current user",
        )
    return team


@module.router.get(
    "/competition/teams/sports/{sport_id}",
    response_model=list[schemas_sport_competition.TeamComplete],
)
async def get_teams_for_sport(
    sport_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: schemas_sport_competition.CompetitionUser = Depends(
        is_user_allowed_to([SportCompetitionPermissions.access_sport_competition]),
    ),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
) -> list[schemas_sport_competition.TeamComplete]:
    sport = await cruds_sport_competition.load_sport_by_id(sport_id, db)
    if sport is None:
        raise HTTPException(
            status_code=404,
            detail="Sport not found in the database",
        )
    return await cruds_sport_competition.load_all_teams_by_sport_id(
        sport_id,
        edition.id,
        db,
    )


@module.router.get(
    "/competition/teams/schools/{school_id}",
    response_model=list[schemas_sport_competition.TeamComplete],
)
async def get_teams_for_school(
    school_id: UUID,
    db: AsyncSession = Depends(get_db),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([SportCompetitionPermissions.access_sport_competition]),
    ),
) -> list[schemas_sport_competition.TeamComplete]:
    school = await cruds_sport_competition.load_school_by_id(school_id, db)
    if school is None:
        raise HTTPException(
            status_code=404,
            detail="School not found in the database",
        )
    return await cruds_sport_competition.load_all_teams_by_school_id(
        school_id,
        edition.id,
        db,
    )


@module.router.get(
    "/competition/teams/sports/{sport_id}/schools/{school_id}",
    response_model=list[schemas_sport_competition.TeamComplete],
)
async def get_sport_teams_for_school_and_sport(
    school_id: UUID,
    sport_id: UUID,
    db: AsyncSession = Depends(get_db),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([SportCompetitionPermissions.access_sport_competition]),
    ),
) -> list[schemas_sport_competition.TeamComplete]:
    school = await cruds_sport_competition.load_school_by_id(school_id, db)
    if school is None:
        raise HTTPException(
            status_code=404,
            detail="School not found in the database",
        )
    sport = await cruds_sport_competition.load_sport_by_id(sport_id, db)
    if sport is None:
        raise HTTPException(
            status_code=404,
            detail="Sport not found in the database",
        )
    return await cruds_sport_competition.load_all_teams_by_school_and_sport_ids(
        school_id,
        sport_id,
        edition.id,
        db,
    )


@module.router.post(
    "/competition/teams",
    status_code=201,
    response_model=schemas_sport_competition.Team,
)
async def create_team(
    team_info: schemas_sport_competition.TeamInfo,
    db: AsyncSession = Depends(get_db),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
    user: schemas_users.CoreUser = Depends(
        is_user_allowed_to([SportCompetitionPermissions.access_sport_competition]),
    ),
) -> schemas_sport_competition.Team:
    if not edition.inscription_enabled:
        raise HTTPException(
            status_code=400,
            detail="Inscriptions are not enabled for the current edition",
        )

    if not (
        await has_user_permission(
            user,
            SportCompetitionPermissions.manage_sport_competition,
            db,
        )
    ) and (user.id != team_info.captain_id or user.school_id != team_info.school_id):
        raise HTTPException(
            status_code=403,
            detail="Unauthorized action",
        )
    sport = await cruds_sport_competition.load_sport_by_id(team_info.sport_id, db)
    if sport is None:
        raise HTTPException(
            status_code=404,
            detail="Sport not found in the database",
        )
    if sport.team_size == 1:
        raise HTTPException(
            status_code=400,
            detail="Sport does not support teams, only individual participants",
        )
    global_team = await cruds_sport_competition.load_team_by_name(
        team_info.name,
        edition.id,
        db,
    )
    if global_team is not None:
        raise HTTPException(status_code=400, detail="Team name already taken")
    captain = await cruds_sport_competition.load_competition_user_by_id(
        team_info.captain_id,
        edition.id,
        db,
    )
    if (
        captain is None
        or captain.user.school_id != team_info.school_id
        or not checksport_category_compatibility(
            captain.sport_category,
            sport.sport_category,
        )
    ):
        raise HTTPException(
            status_code=404,
            detail="Captain user not found",
        )
    nb_teams = await cruds_sport_competition.count_teams_by_school_and_sport_ids(
        team_info.school_id,
        team_info.sport_id,
        edition.id,
        db,
    )
    quotas = await cruds_sport_competition.load_sport_quota_by_ids(
        team_info.school_id,
        team_info.sport_id,
        edition.id,
        db,
    )
    if quotas is not None and quotas.team_quota is not None:
        if nb_teams >= quotas.team_quota:
            raise HTTPException(status_code=400, detail="Team quota reached")
    team = schemas_sport_competition.Team(
        id=uuid4(),
        school_id=team_info.school_id,
        sport_id=team_info.sport_id,
        name=team_info.name,
        captain_id=team_info.captain_id,
        edition_id=edition.id,
        created_at=datetime.now(UTC),
    )
    await cruds_sport_competition.add_team(team, db)
    return team


@module.router.patch(
    "/competition/teams/{team_id}",
    status_code=204,
)
async def edit_team(
    team_id: UUID,
    team_info: schemas_sport_competition.TeamEdit,
    db: AsyncSession = Depends(get_db),
    user: schemas_users.CoreUser = Depends(
        is_user_allowed_to([SportCompetitionPermissions.access_sport_competition]),
    ),
) -> None:
    stored = await cruds_sport_competition.load_team_by_id(team_id, db)
    if stored is None:
        raise HTTPException(
            status_code=404,
            detail="Team not found in the database",
        )
    user_competition_groups = (
        await cruds_sport_competition.load_user_competition_groups_memberships(
            user.id,
            stored.edition_id,
            db,
        )
    )
    if (
        user.id != stored.captain_id
        and not (
            await has_user_permission(
                user,
                SportCompetitionPermissions.manage_sport_competition,
                db,
            )
        )
        and (
            CompetitionGroupType.schools_bds
            not in [group.group for group in user_competition_groups]
            or user.school_id != stored.school_id
        )
    ):
        raise HTTPException(status_code=403, detail="Unauthorized action")
    if team_info.captain_id is not None and team_info.captain_id != stored.captain_id:
        sport = await cruds_sport_competition.load_sport_by_id(
            stored.sport_id,
            db,
        )
        if sport is None:
            raise HTTPException(
                status_code=404,
                detail="Sport not found in the database",
            )
        captain = await cruds_sport_competition.load_competition_user_by_id(
            team_info.captain_id,
            stored.edition_id,
            db,
        )
        if (
            captain is None
            or captain.user.school_id != stored.school_id
            or not checksport_category_compatibility(
                captain.sport_category,
                sport.sport_category,
            )
        ):
            raise HTTPException(
                status_code=404,
                detail="Captain user not found",
            )
    if team_info.name is not None and team_info.name != stored.name:
        global_team = await cruds_sport_competition.load_team_by_name(
            team_info.name,
            stored.edition_id,
            db,
        )
        if global_team is not None:
            raise HTTPException(
                status_code=400,
                detail="Team with this name already exists",
            )
    await cruds_sport_competition.update_team(team_id, team_info, db)


@module.router.delete(
    "/competition/teams/{team_id}",
    status_code=204,
)
async def delete_team(
    team_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: schemas_users.CoreUser = Depends(
        is_user_allowed_to([SportCompetitionPermissions.access_sport_competition]),
    ),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
) -> None:
    stored = await cruds_sport_competition.load_team_by_id(team_id, db)
    if stored is None:
        raise HTTPException(
            status_code=404,
            detail="Team not found in the database",
        )
    user_competition_groups = (
        await cruds_sport_competition.load_user_competition_groups_memberships(
            user.id,
            edition.id,
            db,
        )
    )
    if (
        user.id != stored.captain_id
        and not (
            await has_user_permission(
                user,
                SportCompetitionPermissions.manage_sport_competition,
                db,
            )
        )
        and (
            CompetitionGroupType.schools_bds
            not in [group.group for group in user_competition_groups]
            or user.school_id != stored.school_id
        )
    ):
        raise HTTPException(status_code=403, detail="Unauthorized action")
    await cruds_sport_competition.delete_team_by_id(stored.id, db)


# endregion: Teams
# region: Participants


@module.router.get(
    "/competition/participants/me",
    response_model=schemas_sport_competition.ParticipantComplete,
)
async def get_current_user_participant(
    db: AsyncSession = Depends(get_db),
    user: schemas_users.CoreUser = Depends(
        is_user_allowed_to([SportCompetitionPermissions.access_sport_competition]),
    ),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
) -> schemas_sport_competition.ParticipantComplete:
    participant = await cruds_sport_competition.load_participant_by_user_id(
        user.id,
        edition.id,
        db,
    )
    if participant is None:
        raise HTTPException(
            status_code=404,
            detail="Participant not found in the database",
        )
    return participant


@module.router.get(
    "/competition/participants/sports/{sport_id}",
    response_model=list[schemas_sport_competition.ParticipantComplete],
)
async def get_participants_for_sport(
    sport_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: schemas_users.CoreUser = Depends(
        is_user_allowed_to([SportCompetitionPermissions.access_sport_competition]),
    ),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
) -> list[schemas_sport_competition.ParticipantComplete]:
    sport = await cruds_sport_competition.load_sport_by_id(sport_id, db)
    if sport is None:
        raise HTTPException(
            status_code=404,
            detail="Sport not found in the database",
        )
    return await cruds_sport_competition.load_participants_by_sport_id(
        sport_id,
        edition.id,
        db,
    )


@module.router.get(
    "/competition/participants/schools/{school_id}",
    response_model=list[schemas_sport_competition.ParticipantComplete],
)
async def get_participants_for_school(
    school_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: schemas_users.CoreUser = Depends(
        is_user_allowed_to([SportCompetitionPermissions.access_sport_competition]),
    ),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
) -> list[schemas_sport_competition.ParticipantComplete]:
    if (
        not (
            await has_user_permission(
                user,
                SportCompetitionPermissions.manage_sport_competition,
                db,
            )
        )
        and user.school_id != school_id
    ):
        raise HTTPException(
            status_code=403,
            detail="Unauthorized action",
        )
    return await cruds_sport_competition.load_participants_by_school_id(
        school_id,
        edition.id,
        db,
    )


@module.router.get(
    "/competition/participants/users/{user_id}/certificate",
    response_class=FileResponse,
)
async def download_participant_certificate(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([SportCompetitionPermissions.access_sport_competition]),
    ),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
) -> FileResponse:
    if (
        not (
            await has_user_permission(
                user,
                SportCompetitionPermissions.manage_sport_competition,
                db,
            )
        )
        and user.id != user_id
    ):
        raise HTTPException(
            status_code=403,
            detail="Unauthorized action",
        )
    participant = await cruds_sport_competition.load_participant_by_user_id(
        user_id,
        edition.id,
        db,
    )
    if participant is None:
        raise HTTPException(
            status_code=404,
            detail="Participant not found in the database",
        )
    if participant.certificate_file_id is None:
        raise HTTPException(
            status_code=404,
            detail="No certificate uploaded for this participant",
        )
    return get_file_from_data(
        directory="sport_competition/certificates",
        filename=str(participant.certificate_file_id),
    )


@module.router.post(
    "/competition/sports/{sport_id}/participate",
    status_code=201,
    response_model=schemas_sport_competition.Participant,
)
async def join_sport(
    sport_id: UUID,
    participant_info: schemas_sport_competition.ParticipantInfo,
    db: AsyncSession = Depends(get_db),
    user: schemas_sport_competition.CompetitionUser = Depends(is_competition_user()),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
) -> schemas_sport_competition.Participant:
    if not edition.inscription_enabled:
        raise HTTPException(
            status_code=400,
            detail="Inscriptions are not enabled for this edition",
        )
    school_extension = await cruds_sport_competition.load_school_base_by_id(
        user.user.school_id,
        db,
    )
    if school_extension is None or not school_extension.active:
        raise HTTPException(
            status_code=403,
            detail="User school is not registered for the competition",
        )
    if not school_extension.inscription_enabled:
        raise HTTPException(
            status_code=403,
            detail="Inscriptions are not enabled for user school",
        )
    sport = await cruds_sport_competition.load_sport_by_id(sport_id, db)
    if sport is None:
        raise HTTPException(
            status_code=404,
            detail="Sport not found in the database",
        )
    school = await cruds_sport_competition.load_school_by_id(
        user.user.school_id,
        db,
    )
    if school is None:
        raise HTTPException(
            status_code=500,
            detail="School not found in the database",
        )
    participant_db = await cruds_sport_competition.load_participant_by_user_id(
        user.user_id,
        edition.id,
        db,
    )
    if participant_db is not None:
        raise HTTPException(
            status_code=400,
            detail="User already registered for a sport",
        )
    if not checksport_category_compatibility(
        user.sport_category,
        sport.sport_category,
    ):
        raise HTTPException(
            status_code=403,
            detail="Sport category does not match user sport category",
        )
    if sport.team_size > 1:
        if participant_info.team_id is None:
            raise HTTPException(
                status_code=400,
                detail="Sport declared needs to be played in a team",
            )
        team = await cruds_sport_competition.load_team_by_id(
            participant_info.team_id,
            db,
        )
        if team is None:
            raise HTTPException(
                status_code=404,
                detail="Team not found in the database",
            )
        if team.sport_id != sport_id:
            raise HTTPException(
                status_code=400,
                detail="Team does not belong to the sport",
            )
        if team.school_id != user.user.school_id:
            raise HTTPException(
                status_code=403,
                detail="Unauthorized action, team does not belong to user school",
            )
        if (
            not participant_info.substitute
            and len(
                [user for user in team.participants if not user.substitute],
            )
            >= sport.team_size
        ):
            raise HTTPException(
                status_code=400,
                detail="Maximum number of players in the team reached",
            )
        if (
            participant_info.substitute
            and sport.substitute_max is not None
            and len(
                [user for user in team.participants if user.substitute],
            )
            >= sport.substitute_max
        ):
            raise HTTPException(
                status_code=400,
                detail="Maximum number of substitutes in the team reached",
            )

    elif participant_info.team_id is not None:
        raise HTTPException(
            status_code=400,
            detail="Sport declared needs to be played individually",
        )
    else:
        new_team = schemas_sport_competition.Team(
            id=uuid4(),
            edition_id=edition.id,
            school_id=user.user.school_id,
            sport_id=sport_id,
            captain_id=user.user_id,
            created_at=datetime.now(UTC),
            name=f"{user.user.firstname} {user.user.name}",
        )
        await cruds_sport_competition.add_team(new_team, db)

    participant = schemas_sport_competition.Participant(
        user_id=user.user_id,
        sport_id=sport_id,
        edition_id=edition.id,
        school_id=user.user.school_id,
        license=participant_info.license,
        substitute=participant_info.substitute,
        is_license_valid=False,
        team_id=participant_info.team_id or new_team.id,
    )
    await cruds_sport_competition.add_participant(
        participant,
        db,
    )
    return participant


@module.router.post(
    "/competition/participants/sports/{sport_id}/certificate",
    status_code=204,
)
async def upload_participant_certificate(
    sport_id: UUID,
    certificate: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([SportCompetitionPermissions.access_sport_competition]),
    ),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
) -> None:
    participant = await cruds_sport_competition.load_participant_by_ids(
        user.id,
        sport_id,
        edition.id,
        db,
    )
    if participant is None:
        raise HTTPException(
            status_code=404,
            detail="Participant not found in the database",
        )
    filename = uuid4()
    if participant.certificate_file_id is not None:
        filename = participant.certificate_file_id
    await save_file_as_data(
        upload_file=certificate,
        directory="sport_competition/certificates",
        filename=str(filename),
        max_file_size=4 * 1024 * 1024,  # 4 MB
        accepted_content_types=[
            ContentType.jpg,
            ContentType.png,
            ContentType.pdf,
        ],  # TODO : Change this value
    )
    await cruds_sport_competition.update_participant_certificate_file_id(
        user.id,
        sport_id,
        edition.id,
        filename,
        db,
    )


@module.router.patch(
    "/competition/participants/sports/{sport_id}/users/{user_id}",
    status_code=201,
    response_model=schemas_sport_competition.Participant,
)
async def edit_participant(
    sport_id: UUID,
    user_id: str,
    participant_edit: schemas_sport_competition.ParticipantEdit,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([SportCompetitionPermissions.manage_sport_competition]),
    ),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
) -> schemas_sport_competition.Participant:
    participant = await cruds_sport_competition.load_participant_by_ids(
        user_id,
        sport_id,
        edition.id,
        db,
    )
    if participant is None:
        raise HTTPException(
            status_code=404,
            detail="Participant not found in the database",
        )
    delete_old_team = False
    if (
        participant_edit.sport_id is not None
        and participant_edit.sport_id != participant.sport_id
    ):
        new_sport = await cruds_sport_competition.load_sport_by_id(
            participant_edit.sport_id,
            db,
        )
        if new_sport is None:
            raise HTTPException(
                status_code=404,
                detail="Sport not found in the database",
            )
        if new_sport.team_size > 1:
            if participant.team_id is None:
                raise HTTPException(
                    status_code=400,
                    detail="Sport needs to be played in a team, participant is currently not in a team",
                )
            new_team_db = await cruds_sport_competition.load_team_by_id(
                participant.team_id,
                db,
            )
            if new_team_db is None or new_team_db.sport_id != participant_edit.sport_id:
                raise HTTPException(
                    status_code=400,
                    detail="Participant team is not compatible with the new sport",
                )
        if new_sport.team_size == 1:
            if participant_edit.team_id is not None:
                raise HTTPException(
                    status_code=400,
                    detail="Sport needs to be played individually, participant is currently in a team",
                )
            new_team = schemas_sport_competition.Team(
                id=uuid4(),
                edition_id=edition.id,
                school_id=participant.school_id,
                sport_id=participant_edit.sport_id,
                captain_id=participant.user_id,
                created_at=datetime.now(UTC),
                name=f"{participant.user.user.firstname} {participant.user.user.name}",
            )
            await cruds_sport_competition.add_team(new_team, db)
            participant_edit.team_id = new_team.id
            delete_old_team = True
    if (
        participant_edit.team_id is not None
        and participant_edit.team_id != participant.team_id
    ):
        new_team_db = await cruds_sport_competition.load_team_by_id(
            participant_edit.team_id,
            db,
        )
        if new_team is None:
            raise HTTPException(
                status_code=404,
                detail="Team not found in the database",
            )
        old_team = await cruds_sport_competition.load_team_by_id(
            participant.team_id,
            db,
        )
        if old_team is None:
            raise HTTPException(
                status_code=500,
                detail="Old team not found in the database",
            )
        if len(old_team.participants) == 1:
            delete_old_team = True

    await cruds_sport_competition.update_participant(
        user_id=user_id,
        sport_id=sport_id,
        edition_id=edition.id,
        participant_edit=participant_edit,
        db=db,
    )
    if delete_old_team:
        await cruds_sport_competition.delete_team_by_id(participant.team_id, db)
    return participant


@module.router.patch(
    "/competition/participants/sports/{sport_id}/users/{user_id}/license",
    status_code=204,
)
async def mark_participant_license_as_valid(
    sport_id: UUID,
    user_id: str,
    is_license_valid: bool,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([SportCompetitionPermissions.manage_sport_competition]),
    ),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
) -> None:
    participant = await cruds_sport_competition.load_participant_by_ids(
        user_id,
        sport_id,
        edition.id,
        db,
    )
    if participant is None:
        raise HTTPException(
            status_code=404,
            detail="Participant not found in the database",
        )
    await cruds_sport_competition.update_participant_license_validity(
        user_id,
        sport_id,
        edition.id,
        is_license_valid,
        db,
    )


@module.router.delete(
    "/competition/sports/{sport_id}/withdraw",
    status_code=204,
)
async def withdraw_from_sport(
    sport_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: schemas_sport_competition.CompetitionUser = Depends(is_competition_user()),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
) -> None:
    if not edition.inscription_enabled:
        raise HTTPException(
            status_code=400,
            detail="Inscriptions are not enabled for this edition",
        )

    participant = await cruds_sport_competition.load_participant_by_ids(
        user.user_id,
        sport_id,
        edition.id,
        db,
    )
    if participant is None:
        raise HTTPException(
            status_code=404,
            detail="Participant not found in the database",
        )
    if participant.user.validated:
        await cruds_sport_competition.invalidate_competition_user(
            user.user_id,
            edition.id,
            db,
        )
    await cruds_sport_competition.delete_participant_by_ids(
        user.user_id,
        sport_id,
        edition.id,
        db,
    )
    if participant.certificate_file_id is not None:
        delete_file_from_data(
            directory="sport_competition/certificates",
            filename=str(participant.certificate_file_id),
        )
    team = await cruds_sport_competition.load_team_by_id(
        participant.team_id,
        db,
    )
    if team is not None and len(team.participants) == 0:
        await cruds_sport_competition.delete_team_by_id(team.id, db)


@module.router.delete(
    "/competition/participants/{user_id}/sports/{sport_id}",
    status_code=204,
)
async def delete_participant(
    user_id: str,
    sport_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        has_user_competition_access(
            competition_group=CompetitionGroupType.schools_bds,
        ),
    ),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
) -> None:
    if (
        not (
            await has_user_permission(
                user,
                SportCompetitionPermissions.manage_sport_competition,
                db,
            )
        )
        and not edition.inscription_enabled
    ):
        raise HTTPException(
            status_code=403,
            detail="Editions inscriptions are closed",
        )
    participant = await cruds_sport_competition.load_participant_by_ids(
        user_id,
        sport_id,
        edition.id,
        db,
    )
    if participant is None:
        raise HTTPException(
            status_code=404,
            detail="Participant not found in the database",
        )
    if participant.user.validated:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete a validated participant",
        )
    if (
        not (
            await has_user_permission(
                user,
                SportCompetitionPermissions.manage_sport_competition,
                db,
            )
        )
        and user.school_id != participant.school_id
    ):
        raise HTTPException(
            status_code=403,
            detail="Unauthorized action",
        )
    await cruds_sport_competition.delete_participant_by_ids(
        user_id,
        sport_id,
        edition.id,
        db,
    )
    if participant.certificate_file_id is not None:
        delete_file_from_data(
            directory="sport_competition/certificates",
            filename=str(participant.certificate_file_id),
        )
    team = await cruds_sport_competition.load_team_by_id(
        participant.team_id,
        db,
    )
    if team is not None and len(team.participants) == 0:
        await cruds_sport_competition.delete_team_by_id(team.id, db)


@module.router.delete(
    "/competition/participants/sports/{sport_id}/certificate",
    status_code=204,
)
async def delete_participant_certificate_file(
    sport_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: schemas_users.CoreUser = Depends(
        is_user_allowed_to([SportCompetitionPermissions.access_sport_competition]),
    ),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
) -> None:
    participant = await cruds_sport_competition.load_participant_by_ids(
        user.id,
        sport_id,
        edition.id,
        db,
    )
    if participant is None:
        raise HTTPException(
            status_code=404,
            detail="Participant not found in the database",
        )
    if participant.certificate_file_id is not None:
        await cruds_sport_competition.update_participant_certificate_file_id(
            user.id,
            sport_id,
            edition.id,
            None,
            db,
        )
        delete_file_from_data(
            directory="sport_competition/certificates",
            filename=str(participant.certificate_file_id),
        )


# endregion: Participants
# region: Locations


@module.router.get(
    "/competition/locations",
    response_model=list[schemas_sport_competition.Location],
)
async def get_all_locations(
    db: AsyncSession = Depends(get_db),
    user: schemas_users.CoreUser = Depends(
        is_user_allowed_to([SportCompetitionPermissions.access_sport_competition]),
    ),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
) -> list[schemas_sport_competition.Location]:
    return await cruds_sport_competition.load_all_locations_by_edition_id(
        edition.id,
        db,
    )


@module.router.get(
    "/competition/locations/{location_id}",
    response_model=schemas_sport_competition.LocationComplete,
)
async def get_location_by_id(
    location_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: schemas_users.CoreUser = Depends(
        is_user_allowed_to([SportCompetitionPermissions.access_sport_competition]),
    ),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
) -> schemas_sport_competition.LocationComplete:
    location = await cruds_sport_competition.load_location_by_id(location_id, db)
    if location is None:
        raise HTTPException(
            status_code=404,
            detail="Location not found in the database",
        )
    if location.edition_id != edition.id:
        raise HTTPException(
            status_code=403,
            detail="Location does not belong to the current edition",
        )
    matches = await cruds_sport_competition.load_all_matches_by_location_id(
        location_id,
        db,
    )
    return schemas_sport_competition.LocationComplete(
        id=location.id,
        name=location.name,
        address=location.address,
        latitude=location.latitude,
        longitude=location.longitude,
        edition_id=location.edition_id,
        matches=matches,
    )


@module.router.post(
    "/competition/locations",
    status_code=201,
    response_model=schemas_sport_competition.Location,
)
async def create_location(
    location_info: schemas_sport_competition.LocationBase,
    db: AsyncSession = Depends(get_db),
    user: schemas_users.CoreUser = Depends(
        is_user_allowed_to([SportCompetitionPermissions.manage_sport_competition]),
    ),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
) -> schemas_sport_competition.Location:
    existing_location = await cruds_sport_competition.load_location_by_name(
        location_info.name,
        edition.id,
        db,
    )
    if existing_location is not None:
        raise HTTPException(
            status_code=400,
            detail="Location with this name already exists",
        )
    location = schemas_sport_competition.Location(
        id=uuid4(),
        name=location_info.name,
        address=location_info.address,
        latitude=location_info.latitude,
        longitude=location_info.longitude,
        edition_id=edition.id,
    )
    await cruds_sport_competition.add_location(location, db)
    return location


@module.router.patch(
    "/competition/locations/{location_id}",
    status_code=204,
)
async def edit_location(
    location_id: UUID,
    location_info: schemas_sport_competition.LocationEdit,
    db: AsyncSession = Depends(get_db),
    user: schemas_users.CoreUser = Depends(
        is_user_allowed_to([SportCompetitionPermissions.manage_sport_competition]),
    ),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
) -> None:
    location = await cruds_sport_competition.load_location_by_id(location_id, db)
    if location is None:
        raise HTTPException(
            status_code=404,
            detail="Location not found in the database",
        )
    if location.edition_id != edition.id:
        raise HTTPException(
            status_code=403,
            detail="Location does not belong to the current edition",
        )
    if location_info.name and location_info.name != location.name:
        existing_location = await cruds_sport_competition.load_location_by_name(
            location_info.name,
            edition.id,
            db,
        )
        if existing_location is not None:
            raise HTTPException(
                status_code=400,
                detail="Location with this name already exists",
            )
    await cruds_sport_competition.update_location(location_id, location_info, db)


@module.router.delete(
    "/competition/locations/{location_id}",
    status_code=204,
)
async def delete_location(
    location_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: schemas_users.CoreUser = Depends(
        is_user_allowed_to([SportCompetitionPermissions.manage_sport_competition]),
    ),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
) -> None:
    location = await cruds_sport_competition.load_location_by_id(location_id, db)
    if location is None:
        raise HTTPException(
            status_code=404,
            detail="Location not found in the database",
        )
    if location.edition_id != edition.id:
        raise HTTPException(
            status_code=403,
            detail="Location does not belong to the current edition",
        )
    if await cruds_sport_competition.load_all_matches_by_location_id(
        location_id,
        db,
    ):
        raise HTTPException(
            status_code=400,
            detail="Cannot delete a location with matches scheduled",
        )
    await cruds_sport_competition.delete_location_by_id(location_id, db)


# endregion: Locations
# region: Matches


@module.router.get(
    "/competition/matches",
    response_model=list[schemas_sport_competition.MatchComplete],
)
async def get_all_matches_for_edition(
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([SportCompetitionPermissions.access_sport_competition]),
    ),
) -> list[schemas_sport_competition.MatchComplete]:
    return await cruds_sport_competition.load_all_matches_by_edition_id(
        edition.id,
        db,
    )


@module.router.get(
    "/competition/matches/sports/{sport_id}",
    response_model=list[schemas_sport_competition.MatchComplete],
)
async def get_matches_for_sport_and_edition(
    sport_id: UUID,
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([SportCompetitionPermissions.access_sport_competition]),
    ),
) -> list[schemas_sport_competition.MatchComplete]:
    sport = await cruds_sport_competition.load_sport_by_id(sport_id, db)
    if sport is None:
        raise HTTPException(
            status_code=404,
            detail="Sport not found in the database",
        )
    return await cruds_sport_competition.load_all_matches_by_sport_id(
        sport_id,
        edition.id,
        db,
    )


@module.router.get(
    "/competition/matches/schools/{school_id}",
    response_model=list[schemas_sport_competition.MatchComplete],
)
async def get_matches_for_school_sport_and_edition(
    school_id: UUID,
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([SportCompetitionPermissions.access_sport_competition]),
    ),
) -> list[schemas_sport_competition.MatchComplete]:
    school = await cruds_sport_competition.load_school_by_id(school_id, db)
    if school is None:
        raise HTTPException(
            status_code=404,
            detail="School not found in the database",
        )
    return await cruds_sport_competition.load_all_matches_by_school_id(
        school_id,
        edition.id,
        db,
    )


def check_match_consistency(
    sport_id: UUID,
    match_info: schemas_sport_competition.MatchBase,
    team1: schemas_sport_competition.TeamComplete,
    team2: schemas_sport_competition.TeamComplete,
    edition: schemas_sport_competition.CompetitionEdition,
) -> None:
    if team1.sport_id != sport_id or team2.sport_id != sport_id:
        raise HTTPException(
            status_code=403,
            detail="Teams do not belong to the sport",
        )
    if team1.edition_id != edition.id or team2.edition_id != edition.id:
        raise HTTPException(
            status_code=403,
            detail="Teams do not belong to the current edition",
        )
    if match_info.team1_id == match_info.team2_id:
        raise HTTPException(
            status_code=400,
            detail="Teams cannot play against themselves",
        )
    if match_info.date is not None:
        if match_info.date < edition.start_date:
            raise HTTPException(
                status_code=400,
                detail="Match date is before the edition start date",
            )
        if match_info.date > edition.end_date:
            raise HTTPException(
                status_code=400,
                detail="Match date is after the edition end date",
            )


@module.router.post(
    "/competition/matches/sports/{sport_id}",
    status_code=201,
    response_model=schemas_sport_competition.Match,
)
async def create_match(
    sport_id: UUID,
    match_info: schemas_sport_competition.MatchBase,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        has_user_competition_access(
            competition_group=CompetitionGroupType.sport_manager,
        ),
    ),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
) -> schemas_sport_competition.Match:
    sport = await cruds_sport_competition.load_sport_by_id(sport_id, db)
    if sport is None:
        raise HTTPException(
            status_code=404,
            detail="Sport not found in the database",
        )
    team1 = await cruds_sport_competition.load_team_by_id(match_info.team1_id, db)
    if team1 is None:
        raise HTTPException(
            status_code=404,
            detail="Team 1 not found in the database",
        )
    team2 = await cruds_sport_competition.load_team_by_id(match_info.team2_id, db)
    if team2 is None:
        raise HTTPException(
            status_code=404,
            detail="Team 2 not found in the database",
        )
    location = await cruds_sport_competition.load_location_by_id(
        match_info.location_id,
        db,
    )
    if location is None:
        raise HTTPException(
            status_code=404,
            detail="Location not found in the database",
        )

    check_match_consistency(sport_id, match_info, team1, team2, edition)

    match = schemas_sport_competition.Match(
        id=uuid4(),
        sport_id=sport_id,
        edition_id=edition.id,
        date=match_info.date,
        location_id=match_info.location_id,
        name=match_info.name,
        team1_id=match_info.team1_id,
        team2_id=match_info.team2_id,
        winner_id=None,
        score_team1=None,
        score_team2=None,
    )
    await cruds_sport_competition.add_match(match, db)
    return match


@module.router.patch(
    "/competition/matches/{match_id}",
    status_code=204,
)
async def edit_match(
    match_id: UUID,
    match_info: schemas_sport_competition.MatchEdit,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        has_user_competition_access(
            competition_group=CompetitionGroupType.sport_manager,
        ),
    ),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
) -> None:
    match = await cruds_sport_competition.load_match_by_id(match_id, db)
    if match is None:
        raise HTTPException(
            status_code=404,
            detail="Match not found in the database",
        )
    new_match = match.model_copy(update=match_info.model_dump(exclude_unset=True))

    team1 = await cruds_sport_competition.load_team_by_id(new_match.team1_id, db)
    if team1 is None:
        raise HTTPException(
            status_code=404,
            detail="Team 1 not found in the database",
        )
    team2 = await cruds_sport_competition.load_team_by_id(new_match.team2_id, db)
    if team2 is None:
        raise HTTPException(
            status_code=404,
            detail="Team 2 not found in the database",
        )
    check_match_consistency(match.sport_id, new_match, team1, team2, edition)

    await cruds_sport_competition.update_match(match_id, match_info, db)


@module.router.delete("/competition/matches/{match_id}", status_code=204)
async def delete_match(
    match_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: schemas_users.CoreUser = Depends(
        has_user_competition_access(
            competition_group=CompetitionGroupType.sport_manager,
        ),
    ),
) -> None:
    match = await cruds_sport_competition.load_match_by_id(match_id, db)
    if match is None:
        raise HTTPException(
            status_code=404,
            detail="Match not found in the database",
        )
    await cruds_sport_competition.delete_match_by_id(match_id, db)


# endregion: Matches
# region: Podiums


@module.router.get(
    "/competition/podiums/global",
    response_model=list[schemas_sport_competition.SchoolResult],
    status_code=200,
)
async def get_global_podiums(
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([SportCompetitionPermissions.access_sport_competition]),
    ),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
) -> list[schemas_sport_competition.SchoolResult]:
    """
    Get the global podiums for the current edition.
    """
    return await cruds_sport_competition.get_global_podiums(edition.id, db)


@module.router.get(
    "/competition/podiums/sports/{sport_id}",
    response_model=list[schemas_sport_competition.TeamSportResultComplete],
    status_code=200,
)
async def get_sport_podiums(
    sport_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([SportCompetitionPermissions.access_sport_competition]),
    ),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
) -> list[schemas_sport_competition.TeamSportResultComplete]:
    """
    Get the podiums for a specific sport in the current edition.
    """
    sport = await cruds_sport_competition.load_sport_by_id(sport_id, db)
    if sport is None:
        raise HTTPException(
            status_code=404,
            detail="Sport not found.",
        )
    return await cruds_sport_competition.load_sport_podiums(sport_id, edition.id, db)


@module.router.get(
    "/competition/podiums/pompoms",
    response_model=list[schemas_sport_competition.SchoolResult],
    status_code=200,
)
async def get_pompom_podiums(
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([SportCompetitionPermissions.access_sport_competition]),
    ),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
) -> list[schemas_sport_competition.SchoolResult]:
    """
    Get the pompoms podiums in the current edition.
    """
    return await cruds_sport_competition.load_pompom_podiums(edition.id, db)


@module.router.get(
    "/competition/podiums/schools/{school_id}",
    response_model=list[schemas_sport_competition.TeamSportResultComplete],
    status_code=200,
)
async def get_school_podiums(
    school_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([SportCompetitionPermissions.access_sport_competition]),
    ),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
) -> list[schemas_sport_competition.TeamSportResultComplete]:
    """
    Get the podiums for a specific school in the current edition.
    """
    school = await cruds_sport_competition.load_school_by_id(school_id, db)
    if school is None:
        raise HTTPException(
            status_code=404,
            detail="School not found.",
        )
    return await cruds_sport_competition.load_school_podiums(school_id, edition.id, db)


@module.router.post(
    "/competition/podiums/sports/{sport_id}",
    response_model=list[schemas_sport_competition.TeamSportResult],
    status_code=201,
)
async def create_sport_podium(
    sport_id: UUID,
    rankings: schemas_sport_competition.SportPodiumRankings,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        has_user_competition_access(
            competition_group=CompetitionGroupType.sport_manager,
        ),
    ),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
) -> list[schemas_sport_competition.TeamSportResult]:
    """
    Create or update the podium for a specific sport in the current edition.
    """
    sport = await cruds_sport_competition.load_sport_by_id(sport_id, db)
    if sport is None:
        raise HTTPException(
            status_code=404,
            detail="Sport not found.",
        )
    await cruds_sport_competition.delete_sport_ranking(
        sport_id,
        edition.id,
        db,
    )
    ranking_complete = [
        schemas_sport_competition.TeamSportResult(
            team_id=team.team_id,
            school_id=team.school_id,
            sport_id=sport_id,
            edition_id=edition.id,
            rank=i + 1,
            points=team.points,
        )
        for i, team in enumerate(rankings.rankings)
    ]
    await cruds_sport_competition.add_sport_ranking(
        ranking_complete,
        db,
    )
    return ranking_complete


@module.router.post(
    "/competition/podiums/pompoms",
    response_model=list[schemas_sport_competition.SchoolResult],
    status_code=201,
)
async def create_pompom_podium(
    rankings: list[schemas_sport_competition.SchoolResult],
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        has_user_competition_access(
            competition_group=CompetitionGroupType.sport_manager,
        ),
    ),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
) -> list[schemas_sport_competition.SchoolResult]:
    """
    Create or update the pompoms podium in the current edition.
    """
    await cruds_sport_competition.delete_pompom_ranking(
        edition.id,
        db,
    )
    await cruds_sport_competition.add_pompom_ranking(
        rankings,
        edition.id,
        db,
    )
    return rankings


@module.router.delete(
    "/competition/podiums/sports/{sport_id}",
    status_code=204,
)
async def delete_sport_podium(
    sport_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        has_user_competition_access(
            competition_group=CompetitionGroupType.sport_manager,
        ),
    ),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
) -> None:
    """
    Delete the podium for a specific sport in the current edition.
    """
    sport = await cruds_sport_competition.load_sport_by_id(sport_id, db)
    if sport is None:
        raise HTTPException(
            status_code=404,
            detail="Sport not found.",
        )
    await cruds_sport_competition.delete_sport_ranking(
        sport_id,
        edition.id,
        db,
    )


@module.router.delete(
    "/competition/podiums/pompoms",
    status_code=204,
)
async def delete_pompom_podium(
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        has_user_competition_access(
            competition_group=CompetitionGroupType.sport_manager,
        ),
    ),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
) -> None:
    """
    Delete the pompoms podium in the current edition.
    """
    await cruds_sport_competition.delete_pompom_ranking(
        edition.id,
        db,
    )


# endregion: Podiums
# region: Products


@module.router.get(
    "/competition/products",
    response_model=list[schemas_sport_competition.ProductComplete],
    status_code=200,
)
async def get_all_products(
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([SportCompetitionPermissions.access_sport_competition]),
    ),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
):
    """
    Get all products.
    """
    return await cruds_sport_competition.load_products(edition.id, db)


@module.router.post(
    "/competition/products",
    response_model=schemas_sport_competition.ProductComplete,
    status_code=201,
)
async def create_product(
    product: schemas_sport_competition.ProductBase,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([SportCompetitionPermissions.manage_sport_competition]),
    ),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
):
    """
    Create a product.
    """
    db_product = schemas_sport_competition.Product(
        id=uuid4(),
        edition_id=edition.id,
        required=product.required,
        name=product.name,
        description=product.description,
    )
    await cruds_sport_competition.add_product(
        db_product,
        db,
    )
    return db_product


@module.router.patch(
    "/competition/products/{product_id}",
    status_code=204,
)
async def update_product(
    product_id: UUID,
    product: schemas_sport_competition.ProductEdit,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([SportCompetitionPermissions.manage_sport_competition]),
    ),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
):
    """
    Edit a product.

    **User must be a competition admin to use this endpoint**
    """
    db_product = await cruds_sport_competition.load_product_by_id(
        product_id,
        db,
    )
    if db_product is None or db_product.edition_id != edition.id:
        raise HTTPException(
            status_code=404,
            detail="Product not found.",
        )

    await cruds_sport_competition.update_product(
        product_id,
        product,
        db,
    )


@module.router.delete(
    "/competition/products/{product_id}",
    status_code=204,
)
async def delete_product(
    product_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([SportCompetitionPermissions.manage_sport_competition]),
    ),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
):
    """
    Delete a product.

    **User must be a competition admin to use this endpoint**
    """
    variants = await cruds_sport_competition.load_product_variants(
        product_id,
        db,
    )
    if variants:
        raise HTTPException(
            status_code=403,
            detail="You can't delete this product because some variants are related to it.",
        )
    db_product = await cruds_sport_competition.load_product_by_id(
        product_id,
        db,
    )
    if db_product is None or db_product.edition_id != edition.id:
        raise HTTPException(
            status_code=404,
            detail="Product not found.",
        )

    await cruds_sport_competition.delete_product_by_id(
        product_id,
        db,
    )


# endregion: Products
# region: Product Variants


@module.router.get(
    "/competition/products/available",
    response_model=list[schemas_sport_competition.ProductVariantComplete],
    status_code=200,
)
async def get_available_product_variants(
    db: AsyncSession = Depends(get_db),
    user: schemas_sport_competition.CompetitionUser = Depends(is_competition_user()),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
) -> list[schemas_sport_competition.ProductVariantComplete]:
    """
    Get all available product variants of the current edition for this user.
    """
    school_type = ProductSchoolType.centrale
    if user.user.school_id != SchoolType.centrale_lyon.value:
        school = await cruds_sport_competition.load_school_by_id(
            user.user.school_id,
            db,
        )
        if school is None:
            raise HTTPException(
                status_code=500,
                detail="School not found.",
            )
        if school.from_lyon:
            school_type = ProductSchoolType.from_lyon
        else:
            school_type = ProductSchoolType.others
    public_type = get_public_type_from_user(user)

    return await cruds_sport_competition.load_available_product_variants(
        edition.id,
        school_type,
        public_type,
        db,
    )


@module.router.post(
    "/competition/products/{product_id}/variants",
    response_model=schemas_sport_competition.ProductVariant,
    status_code=201,
)
async def create_product_variant(
    product_id: UUID,
    product_variant: schemas_sport_competition.ProductVariantBase,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([SportCompetitionPermissions.manage_sport_competition]),
    ),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
):
    """
    Create a product variant.

    **User must be a competition admin to use this endpoint**
    """
    db_product = await cruds_sport_competition.load_product_by_id(
        product_id,
        db,
    )
    if db_product is None or db_product.edition_id != edition.id:
        raise HTTPException(
            status_code=404,
            detail="Product not found.",
        )

    db_product_variant = schemas_sport_competition.ProductVariant(
        id=uuid4(),
        edition_id=edition.id,
        product_id=product_id,
        name=product_variant.name,
        description=product_variant.description,
        price=product_variant.price,
        enabled=product_variant.enabled,
        unique=product_variant.unique,
        school_type=product_variant.school_type,
        public_type=product_variant.public_type,
    )

    await cruds_sport_competition.add_product_variant(
        db_product_variant,
        db,
    )
    return db_product_variant


@module.router.patch(
    "/competition/products/variants/{variant_id}",
    status_code=204,
)
async def update_product_variant(
    variant_id: UUID,
    product_variant: schemas_sport_competition.ProductVariantEdit,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([SportCompetitionPermissions.manage_sport_competition]),
    ),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
):
    """
    Edit a product variant.

    **User must be a competition admin to use this endpoint**
    """
    db_product_variant = await cruds_sport_competition.load_product_variant_by_id(
        variant_id,
        db,
    )
    if db_product_variant is None or db_product_variant.edition_id != edition.id:
        raise HTTPException(
            status_code=404,
            detail="Product variant not found.",
        )
    if product_variant.price and product_variant.price != db_product_variant.price:
        purchases = await cruds_sport_competition.load_purchases_by_variant_id(
            variant_id,
            db,
        )
        if purchases:
            raise HTTPException(
                status_code=403,
                detail="You can't edit this product variant price because some purchases are related to it.",
            )

    await cruds_sport_competition.update_product_variant(
        variant_id,
        product_variant,
        db,
    )


@module.router.delete(
    "/competition/products/variants/{variant_id}",
    status_code=204,
)
async def delete_product_variant(
    variant_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([SportCompetitionPermissions.manage_sport_competition]),
    ),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
):
    """
    Delete a product variant.

    **User must be a competition admin to use this endpoint**
    """
    db_product_variant = await cruds_sport_competition.load_product_variant_by_id(
        variant_id,
        db,
    )
    if db_product_variant is None or db_product_variant.edition_id != edition.id:
        raise HTTPException(
            status_code=404,
            detail="Product variant not found.",
        )

    purchases = await cruds_sport_competition.load_purchases_by_variant_id(
        variant_id,
        db,
    )
    if purchases:
        raise HTTPException(
            status_code=403,
            detail="You can't edit this product variant because some purchases are related to it.",
        )
    await cruds_sport_competition.delete_product_variant_by_id(
        variant_id,
        db,
    )


# endregion: Product Variants
# region: Purchases


@module.router.get(
    "/competition/purchases/schools/{school_id}",
    response_model=dict[str, list[schemas_sport_competition.PurchaseComplete]],
    status_code=200,
)
async def get_purchases_by_school_id(
    school_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        has_user_competition_access(competition_group=CompetitionGroupType.schools_bds),
    ),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
):
    """
    Get a school's purchases.

    **User must be competition admin to use this endpoint**
    """
    school = await cruds_sport_competition.load_school_by_id(school_id, db)
    if not school:
        raise HTTPException(
            status_code=404,
            detail="School not found.",
        )
    users = await cruds_sport_competition.load_all_competition_users_by_school(
        school_id,
        edition.id,
        db,
    )
    purchases_by_user: dict[str, list[schemas_sport_competition.PurchaseComplete]] = {}
    for db_user in users:
        purchases_by_user[
            db_user.user_id
        ] = await cruds_sport_competition.load_purchases_by_user_id(
            db_user.user_id,
            edition.id,
            db,
        )
    return purchases_by_user


@module.router.get(
    "/competition/purchases/users/{user_id}",
    response_model=list[schemas_sport_competition.Purchase],
    status_code=200,
)
async def get_purchases_by_user_id(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([SportCompetitionPermissions.manage_sport_competition]),
    ),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
):
    """
    Get a user's purchases.

    **User must be competition admin to use this endpoint**
    """
    return await cruds_sport_competition.load_purchases_by_user_id(
        user_id,
        edition.id,
        db,
    )


@module.router.get(
    "/competition/purchases/me",
    response_model=list[schemas_sport_competition.Purchase],
    status_code=200,
)
async def get_my_purchases(
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([SportCompetitionPermissions.access_sport_competition]),
    ),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
):
    return await get_purchases_by_user_id(user.id, db, user, edition)


@module.router.post(
    "/competition/purchases/me",
    response_model=schemas_sport_competition.Purchase,
    status_code=201,
)
async def create_purchase(
    purchase: schemas_sport_competition.PurchaseBase,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([SportCompetitionPermissions.access_sport_competition]),
    ),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
):
    """
    Create a purchase.

    **User must create a purchase for themself**
    """
    if not edition.inscription_enabled:
        raise HTTPException(
            status_code=403,
            detail="You can't make a purchase when inscriptions are closed",
        )

    competition_user = await cruds_sport_competition.load_competition_user_by_id(
        user.id,
        edition.id,
        db,
    )
    if not competition_user:
        raise HTTPException(
            status_code=403,
            detail="You must be registered for the competition to make a purchase",
        )
    school_extension = await cruds_sport_competition.load_school_by_id(
        user.school_id,
        db,
    )
    if not school_extension:
        raise HTTPException(
            status_code=403,
            detail="Your school is not registered for the competition",
        )
    product_variant = await cruds_sport_competition.load_product_variant_by_id(
        purchase.product_variant_id,
        db,
    )
    if not product_variant:
        raise HTTPException(
            status_code=404,
            detail="Invalid product_variant_id",
        )
    validate_product_variant_purchase(
        purchase,
        product_variant,
        competition_user,
        school_extension,
        edition,
    )
    existing_db_purchase = await cruds_sport_competition.load_purchase_by_ids(
        user.id,
        purchase.product_variant_id,
        db,
    )

    db_purchase = schemas_sport_competition.Purchase(
        user_id=user.id,
        product_variant_id=purchase.product_variant_id,
        edition_id=edition.id,
        validated=False,
        quantity=purchase.quantity,
        purchased_on=datetime.now(UTC),
    )
    if competition_user.validated:
        await cruds_sport_competition.invalidate_competition_user(
            competition_user.user_id,
            edition.id,
            db,
        )

    if existing_db_purchase:
        await cruds_sport_competition.update_purchase(
            db=db,
            user_id=user.id,
            product_variant_id=product_variant.id,
            purchase=schemas_sport_competition.PurchaseEdit(
                quantity=purchase.quantity,
            ),
        )
        return db_purchase

    await cruds_sport_competition.add_purchase(
        db_purchase,
        db,
    )
    return db_purchase


@module.router.post(
    "/competition/purchases/users/{user_id}",
    response_model=schemas_sport_competition.Purchase,
    status_code=201,
)
async def create_user_purchase(
    user_id: str,
    purchase: schemas_sport_competition.PurchaseBase,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([SportCompetitionPermissions.manage_sport_competition]),
    ),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
):
    """
    Create a user's purchase.

    **User must be competition admin to use this endpoint**
    """
    competition_user = await cruds_sport_competition.load_competition_user_by_id(
        user_id,
        edition.id,
        db,
    )
    if not competition_user:
        raise HTTPException(
            status_code=403,
            detail="You must be registered for the competition to make a purchase",
        )
    school_extension = await cruds_sport_competition.load_school_by_id(
        competition_user.user.school_id,
        db,
    )
    if not school_extension:
        raise HTTPException(
            status_code=403,
            detail="Your school is not registered for the competition",
        )
    product_variant = await cruds_sport_competition.load_product_variant_by_id(
        purchase.product_variant_id,
        db,
    )
    if not product_variant:
        raise HTTPException(
            status_code=404,
            detail="Invalid product_variant_id",
        )
    validate_product_variant_purchase(
        purchase,
        product_variant,
        competition_user,
        school_extension,
        edition,
    )
    existing_db_purchase = await cruds_sport_competition.load_purchase_by_ids(
        user_id,
        purchase.product_variant_id,
        db,
    )
    if existing_db_purchase:
        raise HTTPException(
            status_code=403,
            detail="This user already has a purchase for this product variant",
        )

    db_purchase = schemas_sport_competition.Purchase(
        user_id=user_id,
        product_variant_id=purchase.product_variant_id,
        edition_id=edition.id,
        validated=False,
        quantity=purchase.quantity,
        purchased_on=datetime.now(UTC),
    )

    await cruds_sport_competition.add_purchase(
        db_purchase,
        db,
    )
    return db_purchase


@module.router.patch(
    "/competition/purchases/users/{user_id}/variants/{variant_id}",
    status_code=204,
)
async def update_user_purchase(
    user_id: str,
    variant_id: UUID,
    purchase: schemas_sport_competition.PurchaseEdit,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([SportCompetitionPermissions.manage_sport_competition]),
    ),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
):
    """
    Edit a user's purchase.

    **User must be competition admin to use this endpoint**
    """
    db_purchase = await cruds_sport_competition.load_purchase_by_ids(
        user_id,
        variant_id,
        db,
    )
    if not db_purchase or db_purchase.edition_id != edition.id:
        raise HTTPException(
            status_code=404,
            detail="Invalid purchase_id",
        )
    if db_purchase.validated and purchase.validated is None:
        purchase.validated = False

    await cruds_sport_competition.update_purchase(
        db=db,
        user_id=user_id,
        product_variant_id=variant_id,
        purchase=purchase,
    )


@module.router.delete(
    "/competition/purchases/{product_variant_id}",
    status_code=204,
)
async def delete_purchase(
    product_variant_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([SportCompetitionPermissions.access_sport_competition]),
    ),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
):
    """
    Delete a purchase.

    **User must delete their own purchase**
    """
    if not edition.inscription_enabled:
        raise HTTPException(
            status_code=403,
            detail="You can't delete a purchase when inscriptions are closed",
        )

    db_purchase = await cruds_sport_competition.load_purchase_by_ids(
        user.id,
        product_variant_id,
        db,
    )
    if not db_purchase or db_purchase.edition_id != edition.id:
        raise HTTPException(
            status_code=404,
            detail="Invalid purchase_id",
        )
    if db_purchase.validated:
        raise HTTPException(
            status_code=403,
            detail="You can't remove a validated purchase",
        )
    competition_user = await cruds_sport_competition.load_competition_user_by_id(
        user.id,
        edition.id,
        db,
    )
    if competition_user and competition_user.validated:
        await cruds_sport_competition.invalidate_competition_user(
            competition_user.user_id,
            edition.id,
            db,
        )

    await cruds_sport_competition.delete_purchase(
        user.id,
        product_variant_id,
        db,
    )


@module.router.delete(
    "/competition/users/{user_id}/purchases/{product_variant_id}",
    status_code=204,
)
async def delete_user_purchase(
    user_id: str,
    product_variant_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([SportCompetitionPermissions.manage_sport_competition]),
    ),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
):
    """
    Delete a user's purchase.

    **User must be competition admin to use this endpoint**
    """
    db_purchase = await cruds_sport_competition.load_purchase_by_ids(
        user_id,
        product_variant_id,
        db,
    )
    if not db_purchase or db_purchase.edition_id != edition.id:
        raise HTTPException(
            status_code=404,
            detail="Invalid purchase_id",
        )

    await cruds_sport_competition.delete_purchase(
        user_id,
        product_variant_id,
        db,
    )


# endregion: Purchases
# region: Payments


@module.router.get(
    "/competition/payments/schools/{school_id}",
    response_model=dict[str, list[schemas_sport_competition.PaymentComplete]],
    status_code=200,
)
async def get_users_payments_by_school_id(
    school_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        has_user_competition_access(competition_group=CompetitionGroupType.schools_bds),
    ),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
):
    """
    Get a school's users payments.

    **User must be competition admin to use this endpoint**
    """
    school = await cruds_sport_competition.load_school_by_id(school_id, db)
    if not school:
        raise HTTPException(
            status_code=404,
            detail="The school does not exist.",
        )
    if user.school_id != school_id and not (
        await has_user_permission(
            user,
            SportCompetitionPermissions.manage_sport_competition,
            db,
        )
    ):
        raise HTTPException(
            status_code=403,
            detail="You're not allowed to see other schools payments.",
        )
    users = await cruds_sport_competition.load_all_competition_users_by_school(
        school_id,
        edition.id,
        db,
    )
    payments_by_user: dict[str, list[schemas_sport_competition.PaymentComplete]] = {}
    for db_user in users:
        payments_by_user[
            db_user.user_id
        ] = await cruds_sport_competition.load_user_payments(
            db_user.user_id,
            edition.id,
            db,
        )
    return payments_by_user


@module.router.get(
    "/competition/users/{user_id}/payments",
    response_model=list[schemas_sport_competition.PaymentComplete],
    status_code=200,
)
async def get_payments_by_user_id(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([SportCompetitionPermissions.access_sport_competition]),
    ),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
):
    """
    Get a user's payments.

    **User must get his own payments or be competition admin to use this endpoint**
    """
    competition_groups = (
        await cruds_sport_competition.load_user_competition_groups_memberships(
            user.id,
            edition.id,
            db,
        )
    )
    user_db = await cruds_users.get_user_by_id(db, user_id)
    if not user_db:
        raise HTTPException(
            status_code=404,
            detail="The user does not exist.",
        )

    if not (
        user_id == user.id
        or not (
            await has_user_permission(
                user,
                SportCompetitionPermissions.manage_sport_competition,
                db,
            )
        )
        or (
            CompetitionGroupType.schools_bds
            in [competition_group.group for competition_group in competition_groups]
            and user.school_id == user_db.school_id
        )
    ):
        raise HTTPException(
            status_code=403,
            detail="You're not allowed to see other users payments.",
        )
    return await cruds_sport_competition.load_user_payments(
        user_id,
        edition.id,
        db,
    )


@module.router.post(
    "/competition/users/{user_id}/payments",
    response_model=schemas_sport_competition.PaymentComplete,
    status_code=201,
)
async def create_payment(
    user_id: str,
    payment: schemas_sport_competition.PaymentBase,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([SportCompetitionPermissions.manage_sport_competition]),
    ),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
):
    """
    Create a payment.

    **User must be competition admin to use this endpoint**
    """
    user_competition = await cruds_sport_competition.load_competition_user_by_id(
        user_id,
        edition.id,
        db,
    )
    if not user_competition:
        raise HTTPException(
            status_code=404,
            detail="The user is not registered for the competition.",
        )
    if not user_competition.validated:
        raise HTTPException(
            status_code=403,
            detail="The user registration is not validated.",
        )

    db_payment = schemas_sport_competition.PaymentComplete(
        id=uuid4(),
        user_id=user_id,
        total=payment.total,
        edition_id=edition.id,
        method=PaiementMethodType.manual,
    )

    purchases = await cruds_sport_competition.load_purchases_by_user_id(
        user_id,
        edition.id,
        db,
    )
    payments = await cruds_sport_competition.load_user_payments(
        user_id,
        edition.id,
        db,
    )

    await validate_purchases(purchases, [*payments, db_payment], db)
    await cruds_sport_competition.add_payment(db_payment, db)
    return db_payment


@module.router.delete(
    "/competition/users/{user_id}/payments/{payment_id}",
    status_code=204,
)
async def delete_payment(
    user_id: str,
    payment_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([SportCompetitionPermissions.manage_sport_competition]),
    ),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
):
    """
    Remove a payment.

    **User must be competition admin to use this endpoint**
    """
    db_payment = await cruds_sport_competition.load_payment_by_id(
        payment_id,
        db,
    )
    if not db_payment:
        raise HTTPException(
            status_code=404,
            detail="Invalid payment_id",
        )
    if db_payment.user_id != user_id:
        raise HTTPException(
            status_code=403,
            detail="user_id and payment are not related.",
        )

    await cruds_sport_competition.delete_payment(
        payment_id=payment_id,
        db=db,
    )
    purchases = await cruds_sport_competition.load_purchases_by_user_id(
        user_id,
        edition.id,
        db,
    )

    amount = db_payment.total
    purchases.sort(key=lambda x: x.purchased_on, reverse=True)
    for purchase in purchases:
        if amount <= 0:
            break
        if not purchase.validated:
            continue
        await cruds_sport_competition.mark_purchase_as_validated(
            purchase.user_id,
            purchase.product_variant_id,
            False,
            db,
        )
        amount -= purchase.product_variant.price * purchase.quantity


@module.router.post(
    "/competition/pay",
    response_model=schemas_sport_competition.PaymentUrl,
    status_code=200,
)
async def get_payment_url(
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([SportCompetitionPermissions.access_sport_competition]),
    ),
    payment_tool: PaymentTool = Depends(
        get_payment_tool(HelloAssoConfigName.CHALLENGER),
    ),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
):
    """
    Get payment url
    """
    if not edition.inscription_enabled:
        raise HTTPException(
            status_code=403,
            detail="Inscriptions are not enabled for this edition.",
        )
    purchases = await cruds_sport_competition.load_purchases_by_user_id(
        user.id,
        edition.id,
        db,
    )
    payments = await cruds_sport_competition.load_user_payments(
        user.id,
        edition.id,
        db,
    )

    purchases_total = sum(
        purchase.product_variant.price * purchase.quantity for purchase in purchases
    )
    payments_total = sum(payment.total for payment in payments)

    amount = purchases_total - payments_total

    if amount < 100:
        raise HTTPException(
            status_code=403,
            detail="Please give an amount in cents, greater than 1€.",
        )
    user_schema = schemas_users.CoreUser(
        account_type=user.account_type,
        school_id=user.school_id,
        id=user.id,
        email=user.email,
        name=user.name,
        firstname=user.firstname,
        created_on=user.created_on,
        groups=[],
    )
    checkout = await payment_tool.init_checkout(
        module=module.root,
        checkout_amount=amount,
        checkout_name=f"Challenge {edition.name}",
        payer_user=user_schema,
        db=db,
    )
    hyperion_error_logger.info(f"Competition: Logging Checkout id {checkout.id}")
    cruds_sport_competition.add_checkout(
        db=db,
        checkout=schemas_sport_competition.Checkout(
            id=uuid4(),
            user_id=user.id,
            edition_id=edition.id,
            checkout_id=checkout.id,
        ),
    )

    return schemas_sport_competition.PaymentUrl(
        url=checkout.payment_url,
    )


# endregion: Payments
# region: Volunteers


@module.router.get(
    "/competition/volunteers/shifts",
    response_model=list[schemas_sport_competition.VolunteerShiftComplete],
    status_code=200,
)
async def get_all_volunteer_shifts(
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to(
            [
                SportCompetitionPermissions.volunteer_sport_competition,
                SportCompetitionPermissions.manage_sport_competition,
            ],
        ),
    ),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
):
    """
    Get all volunteer shifts.
    """
    return await cruds_sport_competition.load_all_volunteer_shifts_by_edition_id(
        edition.id,
        db,
    )


@module.router.post(
    "/competition/volunteers/shifts",
    response_model=schemas_sport_competition.VolunteerShift,
    status_code=201,
)
async def create_volunteer_shift(
    shift: schemas_sport_competition.VolunteerShiftBase,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([SportCompetitionPermissions.manage_sport_competition]),
    ),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
):
    """
    Create a volunteer shift.
    """
    manager = await cruds_users.get_user_by_id(db, shift.manager_id)
    if manager is None:
        raise HTTPException(
            status_code=404,
            detail="Manager user not found.",
        )
    db_shift = schemas_sport_competition.VolunteerShift(
        id=uuid4(),
        edition_id=edition.id,
        name=shift.name,
        manager_id=shift.manager_id,
        description=shift.description,
        value=shift.value,
        start_time=shift.start_time,
        end_time=shift.end_time,
        location=shift.location,
        max_volunteers=shift.max_volunteers,
    )
    await cruds_sport_competition.add_volunteer_shift(
        db_shift,
        db,
    )
    return db_shift


@module.router.patch(
    "/competition/volunteers/shifts/{shift_id}",
    status_code=204,
)
async def update_volunteer_shift(
    shift_id: UUID,
    shift_edit: schemas_sport_competition.VolunteerShiftEdit,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([SportCompetitionPermissions.manage_sport_competition]),
    ),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
):
    """
    Edit a volunteer shift.

    **User must be a competition admin to use this endpoint**
    """
    db_shift = await cruds_sport_competition.load_volunteer_shift_by_id(
        shift_id,
        db,
    )
    if db_shift is None or db_shift.edition_id != edition.id:
        raise HTTPException(
            status_code=404,
            detail="Volunteer shift not found.",
        )

    await cruds_sport_competition.update_volunteer_shift(
        shift_id,
        shift_edit,
        db,
    )


@module.router.delete(
    "/competition/volunteers/shifts/{shift_id}",
    status_code=204,
)
async def delete_volunteer_shift(
    shift_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([SportCompetitionPermissions.manage_sport_competition]),
    ),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
):
    """
    Delete a volunteer shift.

    **User must be a competition admin to use this endpoint**
    """
    db_shift = await cruds_sport_competition.load_volunteer_shift_by_id(
        shift_id,
        db,
    )
    if db_shift is None or db_shift.edition_id != edition.id:
        raise HTTPException(
            status_code=404,
            detail="Volunteer shift not found.",
        )

    await cruds_sport_competition.delete_volunteer_registrations_for_shift(
        shift_id,
        db,
    )

    await cruds_sport_competition.delete_volunteer_shift_by_id(
        shift_id,
        db,
    )


@module.router.get(
    "/competition/volunteers/me",
    response_model=list[schemas_sport_competition.VolunteerRegistrationComplete],
    status_code=200,
)
async def get_my_volunteer_registrations(
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to(
            [
                SportCompetitionPermissions.volunteer_sport_competition,
                SportCompetitionPermissions.manage_sport_competition,
            ],
        ),
    ),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
):
    """
    Get my volunteer registrations.
    """
    return await cruds_sport_competition.load_volunteer_registrations_by_user_id(
        user.id,
        edition.id,
        db,
    )


@module.router.post(
    "/competition/volunteers/shifts/{shift_id}/register",
    status_code=204,
)
async def register_to_volunteer_shift(
    shift_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to(
            [
                SportCompetitionPermissions.volunteer_sport_competition,
                SportCompetitionPermissions.manage_sport_competition,
            ],
        ),
    ),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
):
    """
    Register to a volunteer shift.
    """
    if not user.school_id == SchoolType.centrale_lyon.value:
        raise HTTPException(
            status_code=403,
            detail="You must be a Centrale Lyon student to register to a volunteer shift.",
        )
    db_shift = await cruds_sport_competition.load_volunteer_shift_by_id(
        shift_id,
        db,
    )
    if db_shift is None or db_shift.edition_id != edition.id:
        raise HTTPException(
            status_code=404,
            detail="Volunteer shift not found.",
        )
    if any(registration.user_id == user.id for registration in db_shift.registrations):
        raise HTTPException(
            status_code=400,
            detail="You are already registered to this volunteer shift.",
        )
    if len(db_shift.registrations) >= db_shift.max_volunteers:
        raise HTTPException(
            status_code=400,
            detail="This volunteer shift is full.",
        )

    # Create or update the CompetitionUser with is_volunteer=True
    competition_user = await cruds_sport_competition.load_competition_user_by_id(
        user.id,
        edition.id,
        db,
    )
    if competition_user is None:
        new_user = schemas_sport_competition.CompetitionUserSimple(
            user_id=user.id,
            edition_id=edition.id,
            sport_category=SportCategory.masculine,
            is_volunteer=True,
            validated=False,
            created_at=datetime.now(UTC),
        )
        await cruds_sport_competition.add_competition_user(new_user, db)
    elif not competition_user.is_volunteer:
        await cruds_sport_competition.update_competition_user(
            user.id,
            edition.id,
            schemas_sport_competition.CompetitionUserEdit(is_volunteer=True),
            db,
        )

    db_registration = schemas_sport_competition.VolunteerRegistration(
        user_id=user.id,
        shift_id=shift_id,
        edition_id=edition.id,
        validated=False,
        registered_at=datetime.now(UTC),
    )

    await cruds_sport_competition.add_volunteer_registration(
        db_registration,
        db,
    )


@module.router.patch(
    "/competition/volunteers/shifts/{shift_id}/users/{user_id}/validation",
    status_code=204,
)
async def validate_volunteer_registration(
    shift_id: UUID,
    user_id: str,
    validated: bool = Body(..., embed=True),
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([SportCompetitionPermissions.manage_sport_competition]),
    ),
):
    """
    Validate a volunteer registration.

    **User must be a competition admin to use this endpoint**
    """
    db_registration = await cruds_sport_competition.load_volunteer_registration_by_ids(
        user_id,
        shift_id,
        db,
    )
    if db_registration is None:
        raise HTTPException(
            status_code=404,
            detail="Volunteer registration not found.",
        )

    await cruds_sport_competition.update_volunteer_registration_validation(
        user_id,
        shift_id,
        validated,
        db,
    )


@module.router.delete(
    "/competition/volunteers/shifts/{shift_id}/unregister",
    status_code=204,
)
async def unregister_from_volunteer_shift(
    shift_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to(
            [
                SportCompetitionPermissions.volunteer_sport_competition,
                SportCompetitionPermissions.manage_sport_competition,
            ],
        ),
    ),
):
    """
    Unregister from a volunteer shift.
    """
    db_registration = await cruds_sport_competition.load_volunteer_registration_by_ids(
        user.id,
        shift_id,
        db,
    )
    if db_registration is None:
        raise HTTPException(
            status_code=404,
            detail="Volunteer registration not found.",
        )
    if db_registration.validated:
        raise HTTPException(
            status_code=403,
            detail="You can't unregister from a validated volunteer shift.",
        )

    await cruds_sport_competition.delete_volunteer_registration(
        user.id,
        shift_id,
        db,
    )


# endregion: Volunteers
# region: Data Exporters


@module.router.get(
    "/competition/data-export/users",
    response_class=FileResponse,
    status_code=200,
)
async def export_competition_users_data(
    included_fields: list[ExcelExportParams] = Query(default=[]),
    exclude_non_validated: bool = False,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([SportCompetitionPermissions.manage_sport_competition]),
    ),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
):
    """
    Export competition users data for the current edition as a CSV file.
    """
    users = await cruds_sport_competition.load_all_competition_users(
        edition.id,
        db,
        exclude_non_validated=exclude_non_validated,
        exclude_cancelled=False,
    )
    products = await cruds_sport_competition.load_products(
        edition.id,
        db,
    )
    sports = await cruds_sport_competition.load_all_sports(db)
    schools = await cruds_sport_competition.load_all_schools(edition.id, db)

    participants = None
    if ExcelExportParams.participants in included_fields:
        all_participants = await cruds_sport_competition.load_all_participants(
            edition.id,
            db,
        )
        participants = {p.user_id: p for p in all_participants}
    payments = None
    if ExcelExportParams.payments in included_fields:
        payments = await cruds_sport_competition.load_all_payments(edition.id, db)
    purchases = await cruds_sport_competition.load_all_purchases(edition.id, db)

    excel_io = BytesIO()

    construct_users_excel_with_parameters(
        parameters=included_fields,
        sports=sports,
        schools=schools,
        users=users,
        products=products,
        users_participant=participants,
        users_payments=payments,
        users_purchases=purchases,
        export_io=excel_io,
    )

    res = excel_io.getvalue()

    excel_io.close()

    headers = {
        "Content-Disposition": f'attachment; filename="competition_users_{edition.name}.xlsx"',
    }
    return Response(
        res,
        headers=headers,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@module.router.get(
    "/competition/data-export/schools/{school_id}/users",
    response_class=FileResponse,
    status_code=200,
)
async def export_school_competition_users_data(
    school_id: UUID,
    included_fields: list[ExcelExportParams] = Query(default=[]),
    exclude_non_validated: bool = False,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([SportCompetitionPermissions.manage_sport_competition]),
    ),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
):
    """
    Export competition users data for the current edition as a CSV file.
    """
    users = await cruds_sport_competition.load_all_competition_users_by_school(
        school_id,
        edition.id,
        db,
        exclude_non_validated=exclude_non_validated,
    )
    products = await cruds_sport_competition.load_products(
        edition.id,
        db,
    )
    sports = await cruds_sport_competition.load_all_sports(db)

    participants = None
    if ExcelExportParams.participants in included_fields:
        all_participants = await cruds_sport_competition.load_participants_by_school_id(
            school_id,
            edition.id,
            db,
        )
        participants = {p.user_id: p for p in all_participants}
    payments = None
    if ExcelExportParams.payments in included_fields:
        payments = await cruds_sport_competition.load_school_payments(
            school_id,
            edition.id,
            db,
        )
    purchases = await cruds_sport_competition.load_school_purchases(
        school_id,
        edition.id,
        db,
    )

    excel_io = BytesIO()

    construct_school_users_excel_with_parameters(
        parameters=included_fields,
        sports=sports,
        users=users,
        products=products,
        users_participant=participants,
        users_payments=payments,
        users_purchases=purchases,
        export_io=excel_io,
    )

    res = excel_io.getvalue()

    excel_io.close()

    headers = {
        "Content-Disposition": f'attachment; filename="competition_users_{edition.name}.xlsx"',
    }
    return Response(
        res,
        headers=headers,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@module.router.get(
    "/competition/data-export/participants/captains",
    response_class=FileResponse,
    status_code=200,
)
async def export_participants_captains_data(
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([SportCompetitionPermissions.manage_sport_competition]),
    ),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
):
    """
    Export participants captains data for the current edition as an Excel file.
    """
    teams = await cruds_sport_competition.load_all_teams(
        edition.id,
        db,
    )
    captains = [
        next(
            (
                participant
                for participant in team.participants
                if participant.user_id == team.captain_id
            ),
            None,
        )
        for team in teams
    ]
    true_captains = [captain for captain in captains if captain is not None]
    sports = await cruds_sport_competition.load_all_sports(db)

    excel_io = BytesIO()

    construct_captains_excel(
        sports=sports,
        captains=true_captains,
        export_io=excel_io,
    )

    res = excel_io.getvalue()

    excel_io.close()

    headers = {
        "Content-Disposition": f'attachment; filename="participants_captains_{edition.name}.xlsx"',
    }
    return Response(
        res,
        headers=headers,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@module.router.get(
    "/competition/data-export/schools/{school_id}/quotas",
    response_class=FileResponse,
    status_code=200,
)
async def export_school_quotas_data(
    school_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([SportCompetitionPermissions.manage_sport_competition]),
    ),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
):
    """
    Export school quotas data for the current edition as an Excel file.
    """
    sports = await cruds_sport_competition.load_all_sports(db)
    products = await cruds_sport_competition.load_products(
        edition.id,
        db,
    )
    school_sports_quotas = (
        await cruds_sport_competition.load_all_sport_quotas_by_school_id(
            school_id,
            edition.id,
            db,
        )
    )
    school_general_quotas = await cruds_sport_competition.load_school_general_quota(
        school_id,
        edition.id,
        db,
    )
    school_product_quotas = (
        await cruds_sport_competition.load_all_school_product_quotas(
            school_id,
            edition.id,
            db,
        )
    )

    excel_io = BytesIO()

    construct_school_quotas_excel(
        sports=sports,
        products=products,
        school_sports_quotas=school_sports_quotas,
        school_general_quotas=school_general_quotas,
        school_product_quotas=school_product_quotas,
        export_io=excel_io,
    )

    res = excel_io.getvalue()

    excel_io.close()

    headers = {
        "Content-Disposition": f'attachment; filename="school_quotas_{school_id}_{edition.name}.xlsx"',
    }
    return Response(
        res,
        headers=headers,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@module.router.get(
    "/competition/data-export/sports/{sport_id}/quotas",
    response_class=FileResponse,
    status_code=200,
)
async def export_sport_quotas_data(
    sport_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([SportCompetitionPermissions.manage_sport_competition]),
    ),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
):
    """
    Export sport quotas data for the current edition as an Excel file.
    """
    sport = await cruds_sport_competition.load_sport_by_id(sport_id, db)
    if not sport:
        raise HTTPException(
            status_code=404,
            detail="The sport does not exist.",
        )

    sport_schools_quotas = (
        await cruds_sport_competition.load_all_sport_quotas_by_sport_id(
            sport_id,
            edition.id,
            db,
        )
    )
    schools = await cruds_sport_competition.load_all_schools(edition.id, db)

    excel_io = BytesIO()

    construct_sport_quotas_excel(
        schools=schools,
        school_sports_quotas=sport_schools_quotas,
        export_io=excel_io,
    )

    res = excel_io.getvalue()

    excel_io.close()

    headers = {
        "Content-Disposition": f'attachment; filename="sport_quotas_{sport.name}_{edition.name}.xlsx"',
    }
    return Response(
        res,
        headers=headers,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@module.router.get(
    "/competition/data-export/sports/{sport_id}/participants",
    response_class=FileResponse,
    status_code=200,
)
async def export_sport_participants_data(
    sport_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([SportCompetitionPermissions.manage_sport_competition]),
    ),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
):
    """
    Export sport quotas data for the current edition as an Excel file.
    """
    sport = await cruds_sport_competition.load_sport_by_id(sport_id, db)
    if not sport:
        raise HTTPException(
            status_code=404,
            detail="The sport does not exist.",
        )
    participants = await cruds_sport_competition.load_participants_by_sport_id(
        sport_id,
        edition.id,
        db,
    )
    schools = await cruds_sport_competition.load_all_schools(edition.id, db)
    users_purchases = await cruds_sport_competition.load_all_purchases(edition.id, db)

    excel_io = BytesIO()

    construct_sport_users_excel(
        schools=schools,
        participants=participants,
        users_purchases=users_purchases,
        export_io=excel_io,
    )

    res = excel_io.getvalue()

    excel_io.close()

    headers = {
        "Content-Disposition": f'attachment; filename="sport_quotas_{sport.name}_{edition.name}.xlsx"',
    }
    return Response(
        res,
        headers=headers,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
