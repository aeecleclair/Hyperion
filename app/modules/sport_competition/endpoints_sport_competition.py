import logging
from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import Body, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.groups.groups_type import GroupType, get_account_types_except_externals
from app.core.payment import schemas_payment
from app.core.payment.payment_tool import PaymentTool
from app.core.payment.types_payment import HelloAssoConfigName
from app.core.schools import cruds_schools
from app.core.schools.schools_type import SchoolType
from app.core.users import cruds_users, models_users, schemas_users
from app.core.utils.config import Settings
from app.dependencies import get_db, get_payment_tool, get_settings, is_user, is_user_in
from app.modules.sport_competition import (
    cruds_sport_competition,
    schemas_sport_competition,
)
from app.modules.sport_competition.dependencies_sport_competition import (
    get_current_edition,
    is_competition_user,
)
from app.modules.sport_competition.types_sport_competition import (
    CompetitionGroupType,
    ProductSchoolType,
)
from app.modules.sport_competition.utils.ffsu_scrapper import (
    validate_participant_ffsu_license,
)
from app.modules.sport_competition.utils_sport_competition import (
    checksport_category_compatibility,
    get_public_type_from_user,
)
from app.types.module import Module
from app.utils.tools import is_user_member_of_any_group

hyperion_error_logger = logging.getLogger("hyperion.error")

module = Module(
    root="sport_competition",
    tag="Sport Competition",
    default_allowed_account_types=get_account_types_except_externals(),
)

# region: Sport


@module.router.get(
    "/competition/sports",
    response_model=list[schemas_sport_competition.Sport],
)
async def get_sports(
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user()),
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
    user: schemas_sport_competition.CompetitionUser = Depends(
        is_user_in(
            group_id=GroupType.competition_admin,
        ),
    ),
) -> schemas_sport_competition.Sport:
    stored = await cruds_sport_competition.load_sport_by_name(sport.name, db)
    if stored is not None:
        raise HTTPException(
            status_code=400,
            detail="A sport with this name already exists",
        )
    sport = schemas_sport_competition.Sport(**sport.model_dump(), id=str(uuid4()))
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
    user: schemas_sport_competition.CompetitionUser = Depends(
        is_user_in(
            group_id=GroupType.competition_admin,
        ),
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
    user: schemas_sport_competition.CompetitionUser = Depends(
        is_user_in(
            group_id=GroupType.competition_admin,
        ),
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
    user: models_users.CoreUser = Depends(is_user()),
) -> list[schemas_sport_competition.CompetitionEdition]:
    return await cruds_sport_competition.load_all_editions(db)


@module.router.get(
    "/competition/editions/active",
    response_model=schemas_sport_competition.CompetitionEdition | None,
)
async def get_active_edition(
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user()),
) -> schemas_sport_competition.CompetitionEdition | None:
    """
    Get the currently active competition edition.
    Returns None if no edition is active.
    """
    return await cruds_sport_competition.load_active_edition(db)


@module.router.post(
    "/competition/editions",
    status_code=201,
    response_model=schemas_sport_competition.CompetitionEdition,
)
async def create_edition(
    edition: schemas_sport_competition.CompetitionEditionBase,
    db: AsyncSession = Depends(get_db),
    user: schemas_sport_competition.CompetitionUser = Depends(
        is_user_in(
            group_id=GroupType.competition_admin,
        ),
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
    user: schemas_sport_competition.CompetitionUser = Depends(
        is_user_in(
            group_id=GroupType.competition_admin,
        ),
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
    user: schemas_sport_competition.CompetitionUser = Depends(
        is_user_in(
            group_id=GroupType.competition_admin,
        ),
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
    user: schemas_sport_competition.CompetitionUser = Depends(
        is_user_in(
            group_id=GroupType.competition_admin,
        ),
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
    user: models_users.CoreUser = Depends(is_user()),
) -> list[schemas_sport_competition.CompetitionUser]:
    """
    Get all competition users for the current edition.
    """
    return await cruds_sport_competition.load_all_competition_users(edition.id, db)


@module.router.get(
    "/competition/users/me",
    response_model=schemas_sport_competition.CompetitionUser,
)
async def get_current_user_competition(
    db: AsyncSession = Depends(get_db),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
    user: models_users.CoreUser = Depends(is_user()),
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
        is_user_in(
            group_id=GroupType.competition_admin,
        ),
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
    user: schemas_sport_competition.CompetitionUserBase,
    db: AsyncSession = Depends(get_db),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
    current_user: models_users.CoreUser = Depends(is_user()),
) -> schemas_sport_competition.CompetitionUserSimple:
    """
    Create a competition user for the current edition.
    The user must exist in the core users database.
    """
    existing_competition_user = (
        await cruds_sport_competition.load_competition_user_by_id(
            db=db,
            user_id=current_user.id,
            edition_id=edition.id,
        )
    )
    if existing_competition_user is not None:
        raise HTTPException(
            status_code=400,
            detail="Competition user already exists",
        )
    user_simple = schemas_sport_competition.CompetitionUserSimple(
        user_id=current_user.id,
        edition_id=edition.id,
        is_athlete=user.is_athlete,
        is_cameraman=user.is_cameraman,
        is_pompom=user.is_pompom,
        is_fanfare=user.is_fanfare,
        is_volunteer=user.is_volunteer,
        sport_category=user.sport_category,
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
    user: schemas_sport_competition.CompetitionUserEdit,
    db: AsyncSession = Depends(get_db),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
    current_user: schemas_users.CoreUser = Depends(is_user()),
) -> None:
    """
    Edit the current user's competition user for the current edition.
    The user must exist in the core users database.
    """
    stored = await cruds_sport_competition.load_competition_user_by_id(
        db=db,
        user_id=current_user.id,
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
            detail="Cannot edit a validated competition user",
        )
    await cruds_sport_competition.update_competition_user(
        current_user.id,
        edition.id,
        user,
        db,
    )


@module.router.patch(
    "/competition/users/{user_id}",
    status_code=204,
)
async def edit_competition_user(
    user_id: str,
    user: schemas_sport_competition.CompetitionUserEdit,
    db: AsyncSession = Depends(get_db),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
    current_user: schemas_sport_competition.CompetitionUser = Depends(
        is_user_in(
            group_id=GroupType.competition_admin,
        ),
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
    await cruds_sport_competition.update_competition_user(user_id, edition.id, user, db)


# endregion: Competition User
# region: Competition Groups


@module.router.get(
    "/competition/groups/{group}",
    response_model=list[schemas_sport_competition.UserGroupMembership],
)
async def get_group_members(
    group: CompetitionGroupType,
    db: AsyncSession = Depends(get_db),
    user: schemas_sport_competition.CompetitionUser = Depends(
        is_user_in(
            group_id=GroupType.competition_admin,
        ),
    ),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
) -> list[schemas_sport_competition.UserGroupMembership]:
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
        is_user(),
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
        is_user_in(
            group_id=GroupType.competition_admin,
        ),
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
    user: schemas_sport_competition.CompetitionUser = Depends(
        is_user_in(
            group_id=GroupType.competition_admin,
        ),
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
    user: schemas_sport_competition.CompetitionUser = Depends(
        is_user_in(
            group_id=GroupType.competition_admin,
        ),
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
    user: models_users.CoreUser = Depends(is_user()),
) -> list[schemas_sport_competition.SchoolExtension]:
    return await cruds_sport_competition.load_all_schools(edition.id, db)


@module.router.get(
    "/competition/schools/{school_id}",
    response_model=schemas_sport_competition.SchoolExtensionComplete,
)
async def get_school(
    school_id: UUID,
    db: AsyncSession = Depends(get_db),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
    user: models_users.CoreUser = Depends(is_user()),
) -> schemas_sport_competition.SchoolExtensionComplete:
    school = await cruds_sport_competition.load_school_by_id(school_id, edition.id, db)
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
    user: schemas_sport_competition.CompetitionUser = Depends(
        is_user_in(
            group_id=GroupType.competition_admin,
        ),
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
    user: schemas_sport_competition.CompetitionUser = Depends(
        is_user_in(
            group_id=GroupType.competition_admin,
        ),
    ),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
) -> None:
    stored = await cruds_sport_competition.load_school_by_id(school_id, edition.id, db)
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
    user: schemas_sport_competition.CompetitionUser = Depends(
        is_user_in(
            group_id=GroupType.competition_admin,
        ),
    ),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
) -> None:
    stored = await cruds_sport_competition.load_school_by_id(school_id, edition.id, db)
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


@module.router.post(
    "/competition/schools/{school_id}/general-quota",
    status_code=201,
    response_model=schemas_sport_competition.SchoolGeneralQuota,
)
async def create_school_general_quota(
    school_id: UUID,
    quota_info: schemas_sport_competition.SchoolGeneralQuotaBase,
    db: AsyncSession = Depends(get_db),
    user: schemas_sport_competition.CompetitionUser = Depends(
        is_user_in(
            group_id=GroupType.competition_admin,
        ),
    ),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
) -> schemas_sport_competition.SchoolGeneralQuota:
    school = await cruds_sport_competition.load_school_by_id(school_id, edition.id, db)
    if school is None:
        raise HTTPException(
            status_code=404,
            detail="School not found in the database",
        )
    stored = await cruds_sport_competition.get_school_general_quota(
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
        **quota_info.model_dump(exclude_unset=True),
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
    user: schemas_sport_competition.CompetitionUser = Depends(
        is_user_in(
            group_id=GroupType.competition_admin,
        ),
    ),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
) -> None:
    school = await cruds_sport_competition.load_school_by_id(school_id, edition.id, db)
    if school is None:
        raise HTTPException(
            status_code=404,
            detail="School not found in the database",
        )
    stored = await cruds_sport_competition.get_school_general_quota(
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
    response_model=list[schemas_sport_competition.SportQuota],
)
async def get_quotas_for_sport(
    sport_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: schemas_sport_competition.CompetitionUser = Depends(
        is_user_in(
            group_id=GroupType.competition_admin,
        ),
    ),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
) -> list[schemas_sport_competition.SportQuota]:
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
    "/competition/schools/{school_id}/quotas",
    response_model=list[schemas_sport_competition.SportQuota],
)
async def get_quotas_for_school(
    school_id: UUID,
    db: AsyncSession = Depends(get_db),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
    user: models_users.CoreUser = Depends(is_user()),
) -> list[schemas_sport_competition.SportQuota]:
    school = await cruds_sport_competition.load_school_by_id(school_id, edition.id, db)
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
    user: schemas_sport_competition.CompetitionUser = Depends(
        is_user_in(
            group_id=GroupType.competition_admin,
        ),
    ),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
) -> None:
    school = await cruds_sport_competition.load_school_by_id(school_id, edition.id, db)
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
    quota = schemas_sport_competition.SportQuota(
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
    quota_info: schemas_sport_competition.SportQuotaEdit,
    db: AsyncSession = Depends(get_db),
    user: schemas_sport_competition.CompetitionUser = Depends(
        is_user_in(
            group_id=GroupType.competition_admin,
        ),
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
    user: schemas_sport_competition.CompetitionUser = Depends(
        is_user_in(
            group_id=GroupType.competition_admin,
        ),
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
# region: Teams


@module.router.get(
    "/competition/teams/sports/{sport_id}",
    response_model=list[schemas_sport_competition.TeamComplete],
)
async def get_teams_for_sport(
    sport_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: schemas_sport_competition.CompetitionUser = Depends(
        is_user(),
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
    user: models_users.CoreUser = Depends(is_user()),
) -> list[schemas_sport_competition.TeamComplete]:
    school = await cruds_sport_competition.load_school_by_id(school_id, edition.id, db)
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
    user: schemas_users.CoreUser = Depends(is_user()),
) -> schemas_sport_competition.Team:
    if GroupType.competition_admin.value not in [
        group.id for group in user.groups
    ] and (user.id != team_info.captain_id or user.school_id != team_info.school_id):
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
    user: schemas_users.CoreUser = Depends(is_user()),
) -> None:
    stored = await cruds_sport_competition.load_team_by_id(team_id, db)
    if stored is None:
        raise HTTPException(
            status_code=404,
            detail="Team not found in the database",
        )
    if user.id != stored.captain_id and GroupType.competition_admin.value not in [
        group.id for group in user.groups
    ]:
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
    user: schemas_users.CoreUser = Depends(is_user()),
) -> None:
    stored = await cruds_sport_competition.load_team_by_id(team_id, db)
    if stored is None:
        raise HTTPException(
            status_code=404,
            detail="Team not found in the database",
        )
    if user.id != stored.captain_id and GroupType.competition_admin.value not in [
        group.id for group in user.groups
    ]:
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
    user: schemas_users.CoreUser = Depends(is_user()),
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
    user: schemas_users.CoreUser = Depends(is_user()),
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
    user: schemas_users.CoreUser = Depends(is_user()),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
) -> list[schemas_sport_competition.ParticipantComplete]:
    if (
        GroupType.competition_admin.value not in [group.id for group in user.groups]
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
    sport = await cruds_sport_competition.load_sport_by_id(sport_id, db)
    if sport is None:
        raise HTTPException(
            status_code=404,
            detail="Sport not found in the database",
        )
    school = await cruds_sport_competition.load_school_by_id(
        user.user.school_id,
        edition.id,
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
            name=f"{user.user.firstname} {user.user.name} - {school.school.name}",
        )
        await cruds_sport_competition.add_team(new_team, db)
    is_license_valid = False
    if participant_info.license:
        is_license_valid = validate_participant_ffsu_license(
            school,
            user,
            participant_info.license,
        )
    participant = schemas_sport_competition.Participant(
        user_id=user.user_id,
        sport_id=sport_id,
        edition_id=edition.id,
        school_id=user.user.school_id,
        license=participant_info.license,
        substitute=participant_info.substitute,
        is_license_valid=is_license_valid,
        team_id=participant_info.team_id or new_team.id,
        created_at=datetime.now(UTC),
    )
    await cruds_sport_competition.add_participant(
        participant,
        db,
    )
    return participant


@module.router.patch(
    "/competition/participants/{user_id}/sports/{sport_id}/validate",
    status_code=204,
)
async def validate_participant(
    user_id: str,
    sport_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: schemas_sport_competition.CompetitionUser = Depends(
        is_competition_user(
            competition_group=CompetitionGroupType.schools_bds,
        ),
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
    if participant.is_license_valid is False:
        raise HTTPException(
            status_code=400,
            detail="Participant license is not valid",
        )
    if (
        GroupType.competition_admin.value
        not in [group.id for group in user.user.groups]
        and user.user.school_id != participant.school_id
    ):
        raise HTTPException(
            status_code=403,
            detail="Unauthorized action",
        )
    sport = await cruds_sport_competition.load_sport_by_id(sport_id, db)
    if sport is None:
        raise HTTPException(
            status_code=404,
            detail="Sport not found in the database",
        )
    school_quota = await cruds_sport_competition.load_sport_quota_by_ids(
        user.user.school_id,
        sport_id,
        edition.id,
        db,
    )
    if school_quota is not None and school_quota.participant_quota is not None:
        nb_participants = await cruds_sport_competition.load_validated_participants_number_by_school_and_sport_ids(
            user.user.school_id,
            sport_id,
            edition.id,
            db,
        )
        if nb_participants >= school_quota.participant_quota:
            raise HTTPException(
                status_code=400,
                detail="Participant quota reached",
            )
    await cruds_sport_competition.validate_participant(
        user_id,
        edition.id,
        db,
    )


@module.router.patch(
    "/competition/participants/{user_id}/sports/{sport_id}/invalidate",
    status_code=204,
)
async def invalidate_participant(
    user_id: str,
    sport_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: schemas_sport_competition.CompetitionUser = Depends(
        is_competition_user(
            competition_group=CompetitionGroupType.schools_bds,
        ),
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
    if (
        GroupType.competition_admin.value
        not in [group.id for group in user.user.groups]
        and user.user.school_id != participant.school_id
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
    await cruds_sport_competition.invalidate_participant(
        user_id,
        edition.id,
        db,
    )


@module.router.delete(
    "/competition/participants/{user_id}/sports/{sport_id}",
    status_code=204,
)
async def delete_participant(
    user_id: str,
    sport_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: schemas_sport_competition.CompetitionUser = Depends(
        is_competition_user(
            competition_group=CompetitionGroupType.schools_bds,
        ),
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
    if participant.user.validated:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete a validated participant",
        )
    if (
        GroupType.competition_admin.value
        not in [group.id for group in user.user.groups]
        and user.user.school_id != participant.school_id
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


# endregion: Participants
# region: Locations


@module.router.get(
    "/competition/locations",
    response_model=list[schemas_sport_competition.Location],
)
async def get_all_locations(
    db: AsyncSession = Depends(get_db),
    user: schemas_users.CoreUser = Depends(is_user()),
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
    user: schemas_users.CoreUser = Depends(is_user()),
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
        is_user_in(
            group_id=GroupType.competition_admin,
        ),
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
        is_user_in(
            group_id=GroupType.competition_admin,
        ),
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
        is_user_in(
            group_id=GroupType.competition_admin,
        ),
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
    "/competition/sports/{sport_id}/matches",
    response_model=list[schemas_sport_competition.Match],
)
async def get_matches_for_sport_and_edition(
    sport_id: UUID,
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user()),
) -> list[schemas_sport_competition.Match]:
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
    "/competition/schools/{school_id}/matches",
    response_model=list[schemas_sport_competition.Match],
)
async def get_matches_for_school_sport_and_edition(
    school_id: UUID,
    sport_id: UUID,
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user()),
) -> list[schemas_sport_competition.Match]:
    school = await cruds_sport_competition.load_school_by_id(school_id, edition.id, db)
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
    if match_info.edition_id != edition.id:
        raise HTTPException(
            status_code=400,
            detail="Match edition does not match the current edition",
        )
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
    "/competition/sports/{sport_id}/matches",
    status_code=201,
    response_model=schemas_sport_competition.Match,
)
async def create_match(
    sport_id: UUID,
    match_info: schemas_sport_competition.MatchBase,
    db: AsyncSession = Depends(get_db),
    user: schemas_users.CoreUser = Depends(
        is_user_in(
            group_id=GroupType.competition_admin,
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

    check_match_consistency(sport_id, match_info, team1, team2, edition)

    match = schemas_sport_competition.Match(
        id=uuid4(),
        sport_id=sport_id,
        edition_id=match_info.edition_id,
        datetime=match_info.date,
        location_id=match_info.location_id,
        name=match_info.name,
        team1_id=match_info.team1_id,
        team2_id=match_info.team2_id,
        winner_id=None,
        score_team1=None,
        score_team2=None,
        team1=team1,
        team2=team2,
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
    user: schemas_users.CoreUser = Depends(
        is_user_in(
            group_id=GroupType.competition_admin,
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
    new_match = match.model_copy(update=match_info.model_dump(exclude_unset=True))
    check_match_consistency(match.sport_id, new_match, team1, team2, edition)

    await cruds_sport_competition.update_match(match_id, match_info, db)


@module.router.delete("/competition/matches/{match_id}", status_code=204)
async def delete_match(
    match_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: schemas_users.CoreUser = Depends(is_user()),
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
    user: models_users.CoreUser = Depends(is_user()),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
) -> list[schemas_sport_competition.SchoolResult]:
    """
    Get the global podiums for the current edition.
    """
    return await cruds_sport_competition.get_global_podiums(edition.id, db)


@module.router.get(
    "/competition/podiums/sport/{sport_id}",
    response_model=list[schemas_sport_competition.TeamSportResultComplete],
    status_code=200,
)
async def get_sport_podiums(
    sport_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user()),
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
    return await cruds_sport_competition.get_sport_podiums(sport_id, edition.id, db)


@module.router.get(
    "/competition/podiums/school/{school_id}",
    response_model=list[schemas_sport_competition.TeamSportResultComplete],
    status_code=200,
)
async def get_school_podiums(
    school_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user()),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
) -> list[schemas_sport_competition.TeamSportResultComplete]:
    """
    Get the podiums for a specific school in the current edition.
    """
    school = await cruds_sport_competition.load_school_by_id(school_id, edition.id, db)
    if school is None:
        raise HTTPException(
            status_code=404,
            detail="School not found.",
        )
    return await cruds_sport_competition.get_school_podiums(school_id, edition.id, db)


@module.router.post(
    "/competition/podiums/sport/{sport_id}/",
    response_model=list[schemas_sport_competition.TeamSportResult],
    status_code=201,
)
async def create_sport_podium(
    sport_id: UUID,
    rankings: schemas_sport_competition.SportPodiumRankings,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_competition_user(
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


@module.router.delete(
    "/competition/podiums/sport/{sport_id}/",
    status_code=204,
)
async def delete_sport_podium(
    sport_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_competition_user(
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


# endregion: Podiums
# region: Products


@module.router.get(
    "/competition/products/",
    response_model=list[schemas_sport_competition.ProductComplete],
    status_code=200,
)
async def get_all_products(
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user()),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
):
    """
    Get all products.
    """
    return await cruds_sport_competition.get_products(edition.id, db)


@module.router.post(
    "/competition/products/",
    response_model=schemas_sport_competition.ProductComplete,
    status_code=201,
)
async def create_product(
    product: schemas_sport_competition.ProductBase,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_in(
            group_id=GroupType.competition_admin,
        ),
    ),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
):
    """
    Create a product.
    """
    db_product = schemas_sport_competition.ProductComplete(
        id=uuid4(),
        edition_id=edition.id,
        name=product.name,
        description=product.description,
    )
    await cruds_sport_competition.add_product(
        db_product,
        db,
    )


@module.router.patch(
    "/competition/products/{product_id}/",
    status_code=204,
)
async def update_product(
    product_id: UUID,
    product: schemas_sport_competition.ProductEdit,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_in(
            group_id=GroupType.competition_admin,
        ),
    ),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
):
    """
    Edit a product.

    **User must be part of the seller's group to use this endpoint**
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
    "/competition/products/{product_id}/",
    status_code=204,
)
async def delete_product(
    product_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_in(
            group_id=GroupType.competition_admin,
        ),
    ),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
):
    """
    Delete a product.

    **User must be part of the seller's group to use this endpoint**
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
):
    """
    Get all available product variants of the current edition for this user.
    """
    school_type = ProductSchoolType.centrale
    if user.user.school_id != SchoolType.centrale_lyon.value:
        school = await cruds_sport_competition.load_school_by_id(
            user.user.school_id,
            edition.id,
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
    "/competition/products/{product_id}/variants/",
    response_model=schemas_sport_competition.ProductVariantComplete,
    status_code=201,
)
async def create_product_variant(
    product_id: UUID,
    product_variant: schemas_sport_competition.ProductVariantBase,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_in(
            group_id=GroupType.competition_admin,
        ),
    ),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
):
    """
    Create a product variant.

    **User must be part of the seller's group to use this endpoint**
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

    db_product_variant = schemas_sport_competition.ProductVariantComplete(
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


@module.router.patch(
    "/competition/products/variants/{variant_id}/",
    status_code=204,
)
async def update_product_variant(
    variant_id: UUID,
    product_variant: schemas_sport_competition.ProductVariantEdit,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_in(
            group_id=GroupType.competition_admin,
        ),
    ),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
):
    """
    Edit a product variant.

    **User must be part of the seller's group to use this endpoint**
    """
    db_product_variant = await cruds_sport_competition.load_product_variant_by_id(
        variant_id,
        db,
    )
    if db_product_variant is None:
        raise HTTPException(
            status_code=404,
            detail="Product variant not found.",
        )
    db_product = await cruds_sport_competition.load_product_by_id(
        db_product_variant.product_id,
        db,
    )
    if db_product is None or db_product.edition_id != edition.id:
        raise HTTPException(
            status_code=404,
            detail="Product not found.",
        )

    await cruds_sport_competition.update_product_variant(
        variant_id,
        product_variant,
        db,
    )


@module.router.delete(
    "/competition/products/variants/{variant_id}/",
    status_code=204,
)
async def delete_product_variant(
    product_id: UUID,
    variant_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_in(
            group_id=GroupType.competition_admin,
        ),
    ),
):
    """
    Delete a product variant.

    **User must be part of the seller's group to use this endpoint**
    """
    db_product_variant = await cruds_sport_competition.load_product_variant_by_id(
        variant_id,
        db,
    )
    if db_product_variant is None:
        raise HTTPException(
            status_code=404,
            detail="Product variant not found.",
        )
    db_product = await cruds_sport_competition.load_product_by_id(
        db_product_variant.product_id,
        db,
    )
    if db_product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found.",
        )
    await cruds_sport_competition.delete_product_variant_by_id(
        variant_id,
        db,
    )


# endregion: Product Variants
# region: Purchases


@module.router.get(
    "/competition/purchases/users/{user_id}",
    response_model=list[schemas_sport_competition.Purchase],
    status_code=200,
)
async def get_purchases_by_user_id(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user()),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
):
    """
    Get a user's purchases.

    **User must get his own purchases or be CDR Admin to use this endpoint**
    """
    if not (
        user_id == user.id
        or is_user_member_of_any_group(user, [GroupType.competition_admin])
    ):
        raise HTTPException(
            status_code=403,
            detail="You're not allowed to see other users purchases.",
        )
    return await cruds_sport_competition.load_purchases_by_user_id(
        user_id,
        edition.id,
        db,
    )


@module.router.get(
    "/competition/purchases/me/",
    response_model=list[schemas_sport_competition.Purchase],
    status_code=200,
)
async def get_my_purchases(
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user()),
):
    return await get_purchases_by_user_id(user.id, db, user)


@module.router.post(
    "/competition/purchases/users/{user_id}/",
    response_model=schemas_sport_competition.Purchase,
    status_code=201,
)
async def create_purchase(
    user_id: str,
    purchase: schemas_sport_competition.PurchaseBase,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user()),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
):
    """
    Create a purchase.

    **User must create a purchase for themself and for an online available product or be part of the seller's group to use this endpoint**
    """

    product_variant = await cruds_sport_competition.load_product_variant_by_id(
        purchase.product_variant_id,
        db,
    )
    if not product_variant:
        raise HTTPException(
            status_code=404,
            detail="Invalid product_variant_id",
        )
    db_product = await cruds_sport_competition.load_product_by_id(
        product_variant.product_id,
        db,
    )
    if not db_product or db_product.edition_id != edition.id:
        raise HTTPException(
            status_code=404,
            detail="Invalid product_id",
        )
    existing_db_purchase = await cruds_sport_competition.load_purchase_by_ids(
        user_id,
        purchase.product_variant_id,
        db,
    )

    db_purchase = schemas_sport_competition.Purchase(
        user_id=user_id,
        product_variant_id=purchase.product_variant_id,
        edition_id=edition.id,
        validated=False,
        quantity=purchase.quantity,
        purchased_on=datetime.now(UTC),
    )
    if existing_db_purchase:
        await cruds_sport_competition.update_purchase(
            db=db,
            user_id=user_id,
            product_variant_id=product_variant.id,
            purchase=schemas_sport_competition.PurchaseEdit(
                quantity=purchase.quantity,
            ),
        )
        # cruds_sport_competition.create_action(db, db_action)
        await db.flush()
        return db_purchase

    await cruds_sport_competition.add_purchase(
        db_purchase,
        db,
    )
    # cruds_sport_competition.create_action(db, db_action)
    await db.flush()
    return db_purchase


@module.router.patch(
    "/competition/users/{user_id}/purchases/{product_variant_id}/validated",
    status_code=204,
)
async def mark_purchase_as_validated(
    user_id: str,
    product_variant_id: UUID,
    validated: bool,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_in(GroupType.competition_admin)),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
):
    """
    Validate a purchase.

    **User must be CDR Admin to use this endpoint**
    """
    db_purchase = await cruds_sport_competition.load_purchase_by_ids(
        user_id,
        product_variant_id,
        db,
    )
    if not db_purchase:
        raise HTTPException(
            status_code=404,
            detail="Invalid purchase",
        )

    await cruds_sport_competition.mark_purchase_as_validated(
        db=db,
        user_id=user_id,
        product_variant_id=product_variant_id,
        validated=validated,
    )
    await db.flush()
    return db_purchase


@module.router.delete(
    "/competition/users/{user_id}/purchases/{product_variant_id}/",
    status_code=204,
)
async def delete_purchase(
    user_id: str,
    product_variant_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user()),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
):
    """
    Delete a purchase.

    **User must create a purchase for themself and for an online available product or be part of the seller's group to use this endpoint**
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
    if db_purchase.validated:
        raise HTTPException(
            status_code=403,
            detail="You can't remove a validated purchase",
        )

    # Check if a validated purchase depends on this purchase

    await cruds_sport_competition.delete_purchase(
        user_id,
        product_variant_id,
        db,
    )
    # cruds_sport_competition.create_action(db, db_action)


# endregion: Purchases
# region: Payments


@module.router.get(
    "/competition/users/{user_id}/payments/",
    response_model=list[schemas_sport_competition.PaymentComplete],
    status_code=200,
)
async def get_payments_by_user_id(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user()),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
):
    """
    Get a user's payments.

    **User must get his own payments or be CDR Admin to use this endpoint**
    """
    if not (
        user_id == user.id or is_user_member_of_any_group(user, [GroupType.admin_cdr])
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
    "/competition/users/{user_id}/payments/",
    response_model=schemas_sport_competition.PaymentComplete,
    status_code=201,
)
async def create_payment(
    user_id: str,
    payment: schemas_sport_competition.PaymentBase,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_in(GroupType.admin_cdr)),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
):
    """
    Create a payment.

    **User must be CDR Admin to use this endpoint**
    """
    db_payment = schemas_sport_competition.PaymentComplete(
        id=uuid4(),
        user_id=user_id,
        total=payment.total,
        edition_id=edition.id,
    )

    await cruds_sport_competition.add_payment(db_payment, db)
    # cruds_sport_competition.create_action(db, db_action)
    await db.flush()
    return db_payment


@module.router.delete(
    "/competition/users/{user_id}/payments/{payment_id}/",
    status_code=204,
)
async def delete_payment(
    user_id: str,
    payment_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_in(GroupType.competition_admin)),
):
    """
    Remove a payment.

    **User must be CDR Admin to use this endpoint**
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
    # cruds_sport_competition.create_action(db, db_action)


@module.router.post(
    "/competition/pay/",
    response_model=schemas_sport_competition.PaymentUrl,
    status_code=200,
)
async def get_payment_url(
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user()),
    settings: Settings = Depends(get_settings),
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
    cruds_sport_competition.create_checkout(
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

    amount = purchases_total - payments_total
    if amount == checkout_payment.paid_amount:
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
            if amount == 0:
                break
            if purchase.product_variant.price * purchase.quantity <= amount:
                await cruds_sport_competition.mark_purchase_as_validated(
                    purchase.user_id,
                    purchase.product_variant_id,
                    True,
                    db,
                )
                amount -= purchase.product_variant.price * purchase.quantity

    await cruds_sport_competition.add_payment(db_payment, db)
    # cruds_sport_competition.create_action(db=db, action=db_action)
    await db.flush()


# endregion: Payments
