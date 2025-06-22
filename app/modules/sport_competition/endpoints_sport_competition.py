import logging
from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import Body, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.groups.groups_type import GroupType, get_account_types_except_externals
from app.core.schools import cruds_schools
from app.core.users import cruds_users, models_users, schemas_users
from app.dependencies import get_db, is_user, is_user_in
from app.modules.sport_competition import (
    cruds_sport_competition,
    schemas_sport_competition,
)
from app.modules.sport_competition.dependencies_sport_competition import (
    get_current_edition,
    is_user_a_member_of_extended,
)
from app.modules.sport_competition.types_sport_competition import (
    CompetitionGroupType,
)
from app.types.module import Module

hyperion_error_logger = logging.getLogger("hyperion.error")

module = Module(
    root="sport_competition",
    tag="Sport Competition",
    default_allowed_account_types=get_account_types_except_externals(),
)


@module.router.get(
    "/competition/sports",
    response_model=list[schemas_sport_competition.Sport],
)
async def get_sports(
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user()),
):
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
):
    stored = await cruds_sport_competition.load_sport_by_name(sport.name, db)
    if stored is not None:
        raise HTTPException(
            status_code=400,
            detail="A sport with this name already exists",
        ) from None
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
):
    stored = await cruds_sport_competition.load_sport_by_id(sport_id, db)
    if stored is None:
        raise HTTPException(
            status_code=404,
            detail="Sport not found in the database",
        ) from None
    if sport.name is not None:
        existing_sport = await cruds_sport_competition.load_sport_by_name(
            sport.name,
            db,
        )
        if existing_sport is not None and existing_sport.id != sport_id:
            raise HTTPException(
                status_code=400,
                detail="A sport with this name already exists",
            ) from None
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
):
    stored = await cruds_sport_competition.load_sport_by_id(sport_id, db)
    if stored is None:
        raise HTTPException(
            status_code=404,
            detail="Sport not found in the database",
        ) from None
    if stored.active:
        raise HTTPException(
            status_code=400,
            detail="Sport is activated and cannot be deleted",
        ) from None
    await cruds_sport_competition.delete_sport_by_id(sport_id, db)


@module.router.get(
    "/competition/editions",
    response_model=list[schemas_sport_competition.CompetitionEdition],
)
async def get_editions(
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user()),
):
    return await cruds_sport_competition.load_all_editions(db)


@module.router.get(
    "/competition/editions/active",
    response_model=schemas_sport_competition.CompetitionEdition | None,
)
async def get_active_edition(
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user()),
):
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
):
    stored = await cruds_sport_competition.load_edition_by_name(edition.name, db)
    if stored is not None:
        raise HTTPException(
            status_code=400,
            detail="An edition with this name already exists",
        ) from None
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
):
    """
    Activate a competition edition.
    If another edition is already active, it will be deactivated.
    """
    stored = await cruds_sport_competition.load_edition_by_id(edition_id, db)
    if stored is None:
        raise HTTPException(
            status_code=404,
            detail="Edition not found in the database",
        ) from None
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
):
    """
    Enable inscription for a competition edition.
    The edition must already be active.
    """
    stored = await cruds_sport_competition.load_edition_by_id(edition_id, db)
    if stored is None:
        raise HTTPException(
            status_code=404,
            detail="Edition not found in the database",
        ) from None
    if not stored.active:
        raise HTTPException(
            status_code=400,
            detail="Edition is not active, cannot patch inscription",
        ) from None
    hyperion_error_logger.debug(
        f"Setting inscription enabled to {enable} for edition {edition_id}",
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
):
    stored = await cruds_sport_competition.load_edition_by_id(edition_id, db)
    if stored is None:
        raise HTTPException(
            status_code=404,
            detail="Edition not found in the database",
        ) from None
    await cruds_sport_competition.update_edition(edition_id, edition_edit, db)


@module.router.get(
    "/competition/groups",
    response_model=list[schemas_sport_competition.Group],
)
async def get_groups(
    db: AsyncSession = Depends(get_db),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
    user: models_users.CoreUser = Depends(is_user()),
):
    return await cruds_sport_competition.load_all_groups(edition.id, db)


@module.router.post(
    "/competition/groups",
    status_code=201,
    response_model=schemas_sport_competition.Group,
)
async def create_group(
    group: schemas_sport_competition.GroupBase,
    db: AsyncSession = Depends(get_db),
    user: schemas_sport_competition.CompetitionUser = Depends(
        is_user_in(
            group_id=GroupType.competition_admin,
        ),
    ),
):
    stored = await cruds_sport_competition.load_group_by_name(group.name, db)
    if stored is not None:
        raise HTTPException(status_code=400, detail="Group already exists") from None
    group = schemas_sport_competition.Group(**group.model_dump(), id=str(uuid4()))
    await cruds_sport_competition.add_group(group, db)
    return group


@module.router.patch(
    "/competition/groups/{group_id}",
    status_code=204,
)
async def edit_group(
    group_id: UUID,
    group: schemas_sport_competition.GroupEdit,
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
    stored = await cruds_sport_competition.load_group_by_id(group_id, edition.id, db)
    if stored is None:
        raise HTTPException(status_code=404, detail="Group not found") from None
    await cruds_sport_competition.update_group(group_id, group, db)


@module.router.delete("/competition/groups/{group_id}")
async def delete_group(
    group_id: UUID,
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
    stored = await cruds_sport_competition.load_group_by_id(group_id, edition.id, db)
    if stored is None:
        raise HTTPException(status_code=404, detail="Group not found") from None

    # await cruds_sport_competition.delete_group_membership_by_group_id(group_id, db)

    await cruds_sport_competition.delete_group_by_id(group_id, db)


@module.router.post(
    "/competition/groups/{group_id}/users/{user_id}",
    status_code=201,
    response_model=schemas_sport_competition.UserGroupMembership,
)
async def add_user_to_group(
    group_id: UUID,
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
    group = await cruds_sport_competition.load_group_by_id(group_id, edition.id, db)
    if group is None:
        raise HTTPException(
            status_code=404,
            detail="Group not found in the database",
        ) from None
    user_to_add = await cruds_users.get_user_by_id(db, user_id)
    if user_to_add is None:
        raise HTTPException(
            status_code=404,
            detail="User not found in the database",
        ) from None
    membership = await cruds_sport_competition.load_active_user_memberships(
        user_id,
        edition.id,
        db,
    )
    if group_id in [m.group_id for m in membership]:
        raise HTTPException(
            status_code=400,
            detail="User is already a member of this group",
        ) from None
    await cruds_sport_competition.add_user_to_group(user_id, group_id, edition.id, db)
    return schemas_sport_competition.UserGroupMembership(
        user_id=user_to_add.id,
        group_id=group.id,
        edition_id=edition.id,
    )


@module.router.delete(
    "/competition/groups/{group_id}/users/{user_id}",
    status_code=204,
)
async def remove_user_from_group(
    group_id: UUID,
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
    membership = await cruds_sport_competition.load_active_user_memberships(
        user_id,
        edition.id,
        db,
    )
    if group_id not in [m.group_id for m in membership]:
        raise HTTPException(
            status_code=404,
            detail="User is not a member of this group",
        ) from None
    await cruds_sport_competition.remove_user_from_group(
        user_id,
        group_id,
        edition.id,
        db,
    )


@module.router.post(
    "/competition/schools",
    status_code=201,
    response_model=schemas_sport_competition.SchoolExtension,
)
async def create_school(
    school: schemas_sport_competition.SchoolExtensionBase,
    db: AsyncSession = Depends(get_db),
    user: schemas_sport_competition.CompetitionUser = Depends(
        is_user_in(
            group_id=GroupType.competition_admin,
        ),
    ),
):
    core_school = await cruds_schools.get_school_by_id(db, school.school_id)
    if core_school is None:
        raise HTTPException(
            status_code=404,
            detail="School not found in the database",
        ) from None
    stored = await cruds_sport_competition.load_school_base_by_id(school.school_id, db)
    if stored is not None:
        raise HTTPException(
            status_code=400,
            detail="School extension already exists",
        ) from None
    await cruds_sport_competition.add_school(school, db)
    return school


@module.router.patch(
    "/competition/schools/{school_id}",
    status_code=204,
)
async def edit_school(
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
):
    stored = await cruds_sport_competition.load_school_by_id(school_id, edition.id, db)
    if stored is None:
        raise HTTPException(
            status_code=404,
            detail="School not found in the database",
        ) from None
    await cruds_sport_competition.update_school(school_id, school, db)


@module.router.delete(
    "/competition/schools/{school_id}",
    status_code=204,
)
async def delete_school(
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
):
    stored = await cruds_sport_competition.load_school_by_id(school_id, edition.id, db)
    if stored is None:
        raise HTTPException(
            status_code=404,
            detail="School not found in the database",
        ) from None
    if stored.active:
        raise HTTPException(
            status_code=400,
            detail="School is activated and cannot be deleted",
        ) from None
    await cruds_sport_competition.delete_school_by_id(school_id, db)


@module.router.post(
    "/competition/schools/{school_id}/general_quota",
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
):
    school = await cruds_sport_competition.load_school_by_id(school_id, edition.id, db)
    if school is None:
        raise HTTPException(
            status_code=404,
            detail="School not found in the database",
        ) from None
    stored = await cruds_sport_competition.get_school_general_quota(
        school_id,
        edition.id,
        db,
    )
    if stored is not None:
        raise HTTPException(
            status_code=400,
            detail="General quota already exists for this school",
        ) from None
    quota = schemas_sport_competition.SchoolGeneralQuota(
        school_id=school_id,
        edition_id=edition.id,
        **quota_info.model_dump(exclude_unset=True),
    )
    await cruds_sport_competition.add_school_general_quota(quota, db)
    return quota


@module.router.patch(
    "/competition/schools/{school_id}/general_quota",
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
):
    school = await cruds_sport_competition.load_school_by_id(school_id, edition.id, db)
    if school is None:
        raise HTTPException(
            status_code=404,
            detail="School not found in the database",
        ) from None
    stored = await cruds_sport_competition.get_school_general_quota(
        school_id,
        edition.id,
        db,
    )
    if stored is None:
        raise HTTPException(
            status_code=404,
            detail="General quota not found for this school",
        ) from None
    await cruds_sport_competition.update_school_general_quota(
        school_id,
        edition.id,
        quota_info,
        db,
    )


@module.router.get(
    "/competition/sports/{sport_id}/quotas",
    response_model=list[schemas_sport_competition.Quota],
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
):
    sport = await cruds_sport_competition.load_sport_by_id(sport_id, db)
    if sport is None:
        raise HTTPException(
            status_code=404,
            detail="Sport not found in the database",
        ) from None
    return await cruds_sport_competition.load_all_sport_quotas_by_sport_id(
        sport_id,
        edition.id,
        db,
    )


@module.router.get(
    "/competition/schools/{school_id}/quotas",
    response_model=list[schemas_sport_competition.Quota],
)
async def get_quotas_for_school(
    school_id: UUID,
    db: AsyncSession = Depends(get_db),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
    user: models_users.CoreUser = Depends(is_user()),
):
    school = await cruds_sport_competition.load_school_by_id(school_id, edition.id, db)
    if school is None:
        raise HTTPException(
            status_code=404,
            detail="School not found in the database",
        ) from None
    return await cruds_sport_competition.load_all_sport_quotas_by_school_id(
        school_id,
        edition.id,
        db,
    )


@module.router.post(
    "/competition/schools/{school_id}/sports/{sport_id}/quotas",
    status_code=201,
)
async def create_sport_quota(
    school_id: UUID,
    sport_id: UUID,
    quota_info: schemas_sport_competition.QuotaInfo,
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
    school = await cruds_sport_competition.load_school_by_id(school_id, edition.id, db)
    if school is None:
        raise HTTPException(
            status_code=404,
            detail="School not found in the database",
        ) from None
    sport = await cruds_sport_competition.load_sport_by_id(sport_id, db)
    if sport is None:
        raise HTTPException(
            status_code=404,
            detail="Sport not found in the database",
        ) from None
    stored = await cruds_sport_competition.load_sport_quota_by_ids(
        school_id,
        sport_id,
        edition.id,
        db,
    )
    if stored is not None:
        raise HTTPException(status_code=400, detail="Quota already exists") from None
    quota = schemas_sport_competition.Quota(
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
    quota_info: schemas_sport_competition.QuotaEdit,
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
    school = await cruds_sport_competition.load_school_by_id(school_id, edition.id, db)
    if school is None:
        raise HTTPException(
            status_code=404,
            detail="School not found in the database",
        ) from None
    sport = await cruds_sport_competition.load_sport_by_id(sport_id, db)
    if sport is None:
        raise HTTPException(
            status_code=404,
            detail="Sport not found in the database",
        ) from None
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
        ) from None
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
):
    if edition is None:
        raise HTTPException(
            status_code=404,
            detail="No active edition found in the database",
        ) from None
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
        ) from None
    await cruds_sport_competition.delete_sport_quota_by_ids(
        school_id,
        sport_id,
        edition.id,
        db,
    )


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
):
    return await cruds_sport_competition.load_all_schools(edition.id, db)


async def check_team_consistency(
    school_id: UUID,
    sport_id: UUID,
    team_id: UUID,
    db: AsyncSession,
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
) -> schemas_sport_competition.TeamComplete:
    school = await cruds_sport_competition.load_school_by_id(school_id, edition.id, db)
    if school is None:
        raise HTTPException(
            status_code=404,
            detail="School not found in the database",
        ) from None
    sport = await cruds_sport_competition.load_sport_by_id(sport_id, db)
    if sport is None:
        raise HTTPException(
            status_code=404,
            detail="Sport not found in the database",
        ) from None
    team = await cruds_sport_competition.load_team_by_id(team_id, db)
    if team is None:
        raise HTTPException(
            status_code=404,
            detail="Team not found in the database",
        ) from None
    if team.school_id != school_id or team.sport_id != sport_id:
        raise HTTPException(
            status_code=403,
            detail="Team given does not belong to school and sport",
        ) from None
    return team


@module.router.get(
    "/competition/teams/sports/{sport_id}",
    response_model=list[schemas_sport_competition.Team],
)
async def get_teams_for_sport(
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
):
    sport = await cruds_sport_competition.load_sport_by_id(sport_id, db)
    if sport is None:
        raise HTTPException(
            status_code=404,
            detail="Sport not found in the database",
        ) from None
    return await cruds_sport_competition.load_all_teams_by_sport_id(
        sport_id,
        edition.id,
        db,
    )


@module.router.get(
    "/competition/teams/schools/{school_id}/sports/{sport_id}",
    response_model=list[schemas_sport_competition.Team],
)
async def get_sport_teams_for_school_and_sport(
    school_id: UUID,
    sport_id: UUID,
    db: AsyncSession = Depends(get_db),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
    user: models_users.CoreUser = Depends(is_user()),
):
    school = await cruds_sport_competition.load_school_by_id(school_id, edition.id, db)
    if school is None:
        raise HTTPException(
            status_code=404,
            detail="School not found in the database",
        ) from None
    sport = await cruds_sport_competition.load_sport_by_id(sport_id, db)
    if sport is None:
        raise HTTPException(
            status_code=404,
            detail="Sport not found in the database",
        ) from None
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
):
    if user.id != team_info.captain_id and GroupType.competition_admin.value not in [
        group.id for group in user.groups
    ]:
        raise HTTPException(status_code=403, detail="Unauthorized action") from None
    global_team = await cruds_sport_competition.load_team_by_name(
        team_info.name,
        edition.id,
        db,
    )
    if global_team is not None:
        raise HTTPException(status_code=400, detail="Team already exists") from None
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
            raise HTTPException(status_code=400, detail="Team quota reached") from None
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


@module.router.patch(
    "/competition/teams/{team_id}",
    status_code=204,
)
async def edit_team(
    team_id: UUID,
    team_info: schemas_sport_competition.TeamEdit,
    db: AsyncSession = Depends(get_db),
    user: schemas_users.CoreUser = Depends(is_user()),
):
    stored = await cruds_sport_competition.load_team_by_id(team_id, db)
    if stored is None:
        raise HTTPException(
            status_code=404,
            detail="Team not found in the database",
        ) from None
    if user.id != stored.captain_id and GroupType.competition_admin.value not in [
        group.id for group in user.groups
    ]:
        raise HTTPException(status_code=403, detail="Unauthorized action") from None
    if team_info.captain_id is not None and team_info.captain_id != stored.captain_id:
        captain = await cruds_users.get_user_by_id(
            db,
            team_info.captain_id,
        )
        if captain is None:
            raise HTTPException(
                status_code=404,
                detail="Captain user not found",
            ) from None
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
            ) from None
    await cruds_sport_competition.update_team(team_id, team_info, db)


@module.router.delete(
    "/competition/teams/{team_id}",
    status_code=204,
)
async def delete_team(
    team_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: schemas_users.CoreUser = Depends(is_user()),
):
    stored = await cruds_sport_competition.load_team_by_id(team_id, db)
    if stored is None:
        raise HTTPException(
            status_code=404,
            detail="Team not found in the database",
        ) from None
    if user.id != stored.captain_id and GroupType.competition_admin.value not in [
        group.id for group in user.groups
    ]:
        raise HTTPException(status_code=403, detail="Unauthorized action") from None
    await cruds_sport_competition.delete_team_by_id(stored.id, db)


@module.router.post(
    "/competition/sports/{sport_id}/participate",
    status_code=201,
    response_model=schemas_sport_competition.Participant,
)
async def join_team(
    sport_id: UUID,
    participant_info: schemas_sport_competition.ParticipantInfo,
    db: AsyncSession = Depends(get_db),
    user: schemas_users.CoreUser = Depends(is_user()),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
):
    sport = await cruds_sport_competition.load_sport_by_id(sport_id, db)
    if sport is None:
        raise HTTPException(
            status_code=404,
            detail="Sport not found in the database",
        ) from None
    if sport.team_size > 1:
        if participant_info.team_id is None:
            raise HTTPException(
                status_code=400,
                detail="Sport declared needs to be played in a team",
            ) from None
        await check_team_consistency(
            user.school_id,
            sport_id,
            participant_info.team_id,
            db,
        )
    elif participant_info.team_id is not None:
        raise HTTPException(
            status_code=400,
            detail="Sport declared needs to be played individually",
        ) from None
    participant = schemas_sport_competition.Participant(
        user_id=user.id,
        sport_id=sport_id,
        edition_id=edition.id,
        school_id=user.school_id,
        license=participant_info.license,
        substitute=participant_info.substitute,
        team_id=participant_info.team_id,
        created_at=datetime.now(UTC),
    )
    await cruds_sport_competition.add_participant(
        participant,
        db,
    )
    return participant


@module.router.get(
    "/competition/participants/sports/{sport_id}",
    response_model=list[schemas_sport_competition.ParticipantComplete],
)
async def get_participants_for_sport(
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
):
    sport = await cruds_sport_competition.load_sport_by_id(sport_id, db)
    if sport is None:
        raise HTTPException(
            status_code=404,
            detail="Sport not found in the database",
        ) from None
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
    user: schemas_sport_competition.CompetitionUser = Depends(
        is_user_a_member_of_extended(
            comptition_group_id=CompetitionGroupType.schools_bds,
        ),
    ),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
):
    if (
        GroupType.competition_admin.value
        not in [group.id for group in user.competition_groups]
        and user.school_id != school_id
    ):
        raise HTTPException(
            status_code=403,
            detail="Unauthorized action",
        ) from None
    return await cruds_sport_competition.load_participants_by_school_id(
        school_id,
        edition.id,
        db,
    )


# TODO: change logic to validate CompetitionUser and not CompetitionParticipant
@module.router.patch(
    "/competition/participants/{user_id}/sports/{sport_id}/validate",
    status_code=204,
)
async def validate_participant(
    user_id: str,
    sport_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: schemas_sport_competition.CompetitionUser = Depends(
        is_user_a_member_of_extended(
            comptition_group_id=CompetitionGroupType.schools_bds,
        ),
    ),
    edition: schemas_sport_competition.CompetitionEdition = Depends(
        get_current_edition,
    ),
):
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
        ) from None
    if (
        GroupType.competition_admin.value
        not in [group.id for group in user.competition_groups]
        and user.school_id != participant.school_id
    ):
        raise HTTPException(
            status_code=403,
            detail="Unauthorized action",
        ) from None
    sport = await cruds_sport_competition.load_sport_by_id(sport_id, db)
    if sport is None:
        raise HTTPException(
            status_code=404,
            detail="Sport not found in the database",
        ) from None
    school_quota = await cruds_sport_competition.load_sport_quota_by_ids(
        user.school_id,
        sport_id,
        edition.id,
        db,
    )
    if school_quota is not None and school_quota.participant_quota is not None:
        nb_participants = await cruds_sport_competition.load_validated_participants_number_by_school_and_sport_ids(
            user.school_id,
            sport_id,
            edition.id,
            db,
        )
        if nb_participants >= school_quota.participant_quota:
            raise HTTPException(
                status_code=400,
                detail="Participant quota reached",
            ) from None
    if sport.team_size > 1:
        team = await cruds_sport_competition.load_team_by_id(
            participant.team_id,
            db,
        )
        if team is None:
            raise HTTPException(
                status_code=404,
                detail="Team not found in the database",
            ) from None
        if (
            not participant.substitute
            and len(
                [user for user in team.participants if not user.substitute],
            )
            >= sport.team_size
        ):
            raise HTTPException(
                status_code=400,
                detail="Maximum number of players in the team reached",
            ) from None
        if (
            participant.substitute
            and sport.substitute_max is not None
            and len(
                [user for user in team.participants if user.substitute],
            )
            >= sport.substitute_max
        ):
            raise HTTPException(
                status_code=400,
                detail="Maximum number of substitutes in the team reached",
            ) from None
    await cruds_sport_competition.validate_participant(
        user_id,
        edition.id,
        db,
    )


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
):
    sport = await cruds_sport_competition.load_sport_by_id(sport_id, db)
    if sport is None:
        raise HTTPException(
            status_code=404,
            detail="Sport not found in the database",
        ) from None
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
):
    school = await cruds_sport_competition.load_school_by_id(school_id, edition.id, db)
    if school is None:
        raise HTTPException(
            status_code=404,
            detail="School not found in the database",
        ) from None
    sport = await cruds_sport_competition.load_sport_by_id(sport_id, db)
    if sport is None:
        raise HTTPException(
            status_code=404,
            detail="Sport not found in the database",
        ) from None
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
        ) from None
    if team1.sport_id != sport_id or team2.sport_id != sport_id:
        raise HTTPException(
            status_code=403,
            detail="Teams do not belong to the sport",
        ) from None
    if team1.edition_id != edition.id or team2.edition_id != edition.id:
        raise HTTPException(
            status_code=403,
            detail="Teams do not belong to the current edition",
        ) from None
    if match_info.team1_id == match_info.team2_id:
        raise HTTPException(
            status_code=400,
            detail="Teams cannot play against themselves",
        ) from None
    if match_info.date is not None:
        if match_info.date < edition.start_date:
            raise HTTPException(
                status_code=400,
                detail="Match date is before the edition start date",
            ) from None
        if match_info.date > edition.end_date:
            raise HTTPException(
                status_code=400,
                detail="Match date is after the edition end date",
            ) from None


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
):
    sport = await cruds_sport_competition.load_sport_by_id(sport_id, db)
    if sport is None:
        raise HTTPException(
            status_code=404,
            detail="Sport not found in the database",
        ) from None
    team1 = await cruds_sport_competition.load_team_by_id(match_info.team1_id, db)
    if team1 is None:
        raise HTTPException(
            status_code=404,
            detail="Team 1 not found in the database",
        ) from None
    team2 = await cruds_sport_competition.load_team_by_id(match_info.team2_id, db)
    if team2 is None:
        raise HTTPException(
            status_code=404,
            detail="Team 2 not found in the database",
        ) from None

    check_match_consistency(sport_id, match_info, team1, team2, edition)

    match = schemas_sport_competition.Match(
        id=uuid4(),
        sport_id=sport_id,
        edition_id=match_info.edition_id,
        datetime=match_info.date,
        location=match_info.location,
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
):
    match = await cruds_sport_competition.load_match_by_id(match_id, db)
    if match is None:
        raise HTTPException(
            status_code=404,
            detail="Match not found in the database",
        ) from None
    team1 = await cruds_sport_competition.load_team_by_id(match_info.team1_id, db)
    if team1 is None:
        raise HTTPException(
            status_code=404,
            detail="Team 1 not found in the database",
        ) from None
    team2 = await cruds_sport_competition.load_team_by_id(match_info.team2_id, db)
    if team2 is None:
        raise HTTPException(
            status_code=404,
            detail="Team 2 not found in the database",
        ) from None
    new_match = match.model_copy(update=match_info.model_dump(exclude_unset=True))
    check_match_consistency(match.sport_id, new_match, team1, team2, edition)

    await cruds_sport_competition.update_match(match_id, match_info, db)


@module.router.delete("/competition/matches/{match_id}", status_code=204)
async def delete_match(
    match_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: schemas_users.CoreUser = Depends(is_user()),
):
    match = await cruds_sport_competition.load_match_by_id(match_id, db)
    if match is None:
        raise HTTPException(
            status_code=404,
            detail="Match not found in the database",
        ) from None
    await cruds_sport_competition.delete_match_by_id(match_id, db)
