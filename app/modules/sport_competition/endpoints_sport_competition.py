import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import schemas_core
from app.core.users import cruds_users
from app.dependencies import get_db, is_user
from app.modules.sport_competition import cruds_sport_competition as competition_cruds
from app.modules.sport_competition import (
    schemas_sport_competition as competition_schemas,
)
from app.modules.sport_competition.dependencies_sport_competition import (
    is_user_a_member_of_extended,
)
from app.modules.sport_competition.types_sport_competition import CompetitionGroupType

router = APIRouter(tags=["Sport Competition"])
hyperion_error_logger = logging.getLogger("hyperion.error")


@router.get("/competition/sports", response_model=list[competition_schemas.Sport])
async def get_sports(db: AsyncSession = Depends(get_db)):
    return await competition_cruds.load_all_groups(db)


@router.post(
    "/competition/sports",
    status_code=201,
    response_model=competition_schemas.Sport,
)
async def create_sport(
    sport: competition_schemas.SportBase,
    db: AsyncSession = Depends(get_db),
    user=Depends(
        is_user_a_member_of_extended(
            comptition_group_id=CompetitionGroupType.competition_admin,
        ),
    ),
):
    stored = await competition_cruds.load_sport_by_name(sport.name, db)
    if stored is not None:
        raise HTTPException(
            status_code=400,
            detail="A sport with this name already exists",
        ) from None
    sport = competition_schemas.Sport(**sport.model_dump(), id=str(uuid.uuid4()))
    await competition_cruds.store_sport(sport, db)
    return sport


@router.patch("/competition/sports")
async def edit_sport(
    sport: competition_schemas.SportEdit,
    db: AsyncSession = Depends(get_db),
    user=Depends(
        is_user_a_member_of_extended(
            comptition_group_id=CompetitionGroupType.competition_admin,
        ),
    ),
):
    stored = await competition_cruds.load_sport_by_id(sport.id, db)
    if stored is None:
        raise HTTPException(
            status_code=404,
            detail="Sport not found in the database",
        ) from None
    stored.model_copy(update=sport.model_dump())
    await competition_cruds.store_sport(stored, db)
    return stored


@router.delete("/competition/sports/{sport_id}")
async def delete_sport(
    sport_id: str,
    db: AsyncSession = Depends(get_db),
    user=Depends(
        is_user_a_member_of_extended(
            comptition_group_id=CompetitionGroupType.competition_admin,
        ),
    ),
):
    stored = await competition_cruds.load_sport_by_id(sport_id, db)
    if stored is None:
        raise HTTPException(
            status_code=404,
            detail="Sport not found in the database",
        ) from None
    if stored.activated:
        raise HTTPException(
            status_code=400,
            detail="Sport is activated and cannot be deleted",
        ) from None
    await competition_cruds.delete_sport_by_id(sport_id, db)


@router.get("/competition/groups", response_model=list[competition_schemas.Group])
async def get_groups(db=Depends(get_db)):
    return await competition_cruds.load_all_groups(db)


@router.post(
    "/competition/groups",
    status_code=201,
    response_model=competition_schemas.Group,
)
async def create_group(
    group: competition_schemas.GroupBase,
    db=Depends(get_db),
    user=Depends(
        is_user_a_member_of_extended(
            comptition_group_id=CompetitionGroupType.competition_admin,
        ),
    ),
):
    stored = await competition_cruds.load_group_by_name(group.name, db)
    if stored is not None:
        raise HTTPException(status_code=400, detail="Group already exists") from None
    group = competition_schemas.Group(**group.model_dump(), id=str(uuid.uuid4()))
    await competition_cruds.store_group(group, db)
    return group


@router.patch("/competition/groups")
async def edit_group(
    group: competition_schemas.GroupEdit,
    db=Depends(get_db),
    user=Depends(
        is_user_a_member_of_extended(
            comptition_group_id=CompetitionGroupType.competition_admin,
        ),
    ),
):
    stored = await competition_cruds.load_group_by_id(group.id, db)
    if stored is None:
        raise HTTPException(status_code=404, detail="Group not found") from None
    stored.model_copy(update=group.model_dump())
    await competition_cruds.store_group(stored, db)


@router.delete("/competition/groups/{group_id}")
async def delete_group(
    group_id: str,
    db=Depends(get_db),
    user=Depends(
        is_user_a_member_of_extended(
            comptition_group_id=CompetitionGroupType.competition_admin,
        ),
    ),
):
    stored = await competition_cruds.load_group_by_id(group_id, db)
    if stored is None:
        raise HTTPException(status_code=404, detail="Group not found") from None
    await competition_cruds.delete_group_by_id(group_id, db)


@router.get(
    "/competition/sport/{sport_id}/quotas",
    response_model=list[competition_schemas.Quota],
)
async def get_quotas_for_sport(
    sport_id: str,
    db=Depends(get_db),
    user=Depends(
        is_user_a_member_of_extended(
            comptition_group_id=CompetitionGroupType.competition_admin,
        ),
    ),
):
    edition = await competition_cruds.load_active_edition(db)
    if edition is None:
        raise HTTPException(
            status_code=404,
            detail="No active edition found in the database",
        ) from None
    sport = await competition_cruds.load_sport_by_id(sport_id, db)
    if sport is None:
        raise HTTPException(
            status_code=404,
            detail="Sport not found in the database",
        ) from None
    return await competition_cruds.load_all_quotas_by_sport_id(
        sport_id,
        edition.id,
        db,
    )


@router.get(
    "/competition/school/{school_id}/quotas",
    response_model=list[competition_schemas.Quota],
)
async def get_quotas_for_school(
    school_id: str,
    db=Depends(get_db),
):
    edition = await competition_cruds.load_active_edition(db)
    if edition is None:
        raise HTTPException(
            status_code=404,
            detail="No active edition found in the database",
        ) from None
    school = await competition_cruds.load_school_by_id(school_id, db)
    if school is None:
        raise HTTPException(
            status_code=404,
            detail="School not found in the database",
        ) from None
    return await competition_cruds.load_all_quotas_by_school_id(
        school_id,
        edition.id,
        db,
    )


@router.post("/competition/school/{school_id}/sport/{sport_id}/quotas", status_code=201)
async def create_quota(
    school_id: str,
    sport_id: str,
    quota_info: competition_schemas.QuotaInfo,
    db=Depends(get_db),
    user=Depends(
        is_user_a_member_of_extended(
            comptition_group_id=CompetitionGroupType.competition_admin,
        ),
    ),
):
    edition = await competition_cruds.load_active_edition(db)
    if edition is None:
        raise HTTPException(
            status_code=404,
            detail="No active edition found in the database",
        ) from None
    school = await competition_cruds.load_school_by_id(school_id, db)
    if school is None:
        raise HTTPException(
            status_code=404,
            detail="School not found in the database",
        ) from None
    sport = await competition_cruds.load_sport_by_id(sport_id, db)
    if sport is None:
        raise HTTPException(
            status_code=404,
            detail="Sport not found in the database",
        ) from None
    stored = await competition_cruds.load_quota_by_ids(
        school_id,
        sport_id,
        edition.id,
        db,
    )
    if stored is not None:
        raise HTTPException(status_code=400, detail="Quota already exists") from None
    quota = competition_schemas.Quota(
        school_id=school_id,
        sport_id=sport_id,
        participant_quota=quota_info.participant_quota,
        team_quota=quota_info.team_quota,
        edition_id=edition.id,
    )
    await competition_cruds.store_quota(quota, db)


@router.patch("/competition/school/{school_id}/sport/{sport_id}/quotas")
async def edit_quota(
    school_id: str,
    sport_id: str,
    quota_info: competition_schemas.QuotaEdit,
    db=Depends(get_db),
    user=Depends(
        is_user_a_member_of_extended(
            comptition_group_id=CompetitionGroupType.competition_admin,
        ),
    ),
):
    edition = await competition_cruds.load_active_edition(db)
    if edition is None:
        raise HTTPException(
            status_code=404,
            detail="No active edition found in the database",
        ) from None
    school = await competition_cruds.load_school_by_id(school_id, db)
    if school is None:
        raise HTTPException(
            status_code=404,
            detail="School not found in the database",
        ) from None
    sport = await competition_cruds.load_sport_by_id(sport_id, db)
    if sport is None:
        raise HTTPException(
            status_code=404,
            detail="Sport not found in the database",
        ) from None
    stored = await competition_cruds.load_quota_by_ids(
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
    stored.model_copy(update=quota_info.model_dump())
    await competition_cruds.store_quota(stored, db)


@router.delete("/competition/school/{school_id}/sport/{sport_id}/quotas")
async def delete_quota(
    school_id: str,
    sport_id: str,
    db=Depends(get_db),
    user=Depends(
        is_user_a_member_of_extended(
            comptition_group_id=CompetitionGroupType.competition_admin,
        ),
    ),
):
    edition = await competition_cruds.load_active_edition(db)
    if edition is None:
        raise HTTPException(
            status_code=404,
            detail="No active edition found in the database",
        ) from None
    stored = await competition_cruds.load_quota_by_ids(
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
    await competition_cruds.delete_quota_by_ids(school_id, sport_id, edition.id, db)


@router.get(
    "/competition/schools",
    response_model=list[competition_schemas.SchoolExtension],
)
async def get_schools(db=Depends(get_db)):
    return await competition_cruds.load_all_schools(db)


@router.post(
    "/competition/schools",
    status_code=201,
    response_model=competition_schemas.SchoolExtension,
)
async def create_school(
    school: competition_schemas.SchoolExtension,
    db=Depends(get_db),
    user=Depends(
        is_user_a_member_of_extended(
            comptition_group_id=CompetitionGroupType.competition_admin,
        ),
    ),
):
    stored = await competition_cruds.load_school_by_id(school.id, db)
    if stored is not None:
        raise HTTPException(
            status_code=400,
            detail="School extension already exists",
        ) from None
    await competition_cruds.store_school(school, db)
    return school


@router.patch("/competition/schools")
async def edit_school(
    school: competition_schemas.SchoolExtensionEdit,
    db=Depends(get_db),
    user=Depends(
        is_user_a_member_of_extended(
            comptition_group_id=CompetitionGroupType.competition_admin,
        ),
    ),
):
    stored = await competition_cruds.load_school_by_id(school.id, db)
    if stored is None:
        raise HTTPException(
            status_code=404,
            detail="School not found in the database",
        ) from None
    stored.model_copy(update=school.model_dump())
    await competition_cruds.store_school(stored, db)


@router.delete("/competition/schools/{school_id}")
async def delete_school(
    school_id: str,
    db=Depends(get_db),
    user=Depends(
        is_user_a_member_of_extended(
            comptition_group_id=CompetitionGroupType.competition_admin,
        ),
    ),
):
    stored = await competition_cruds.load_school_by_id(school_id, db)
    if stored is None:
        raise HTTPException(
            status_code=404,
            detail="School not found in the database",
        ) from None
    if stored.activated:
        raise HTTPException(
            status_code=400,
            detail="School is activated and cannot be deleted",
        ) from None
    await competition_cruds.delete_school_by_id(school_id, db)


async def check_team_consistency(
    school_id: str,
    sport_id: str,
    team_id: str,
    db: AsyncSession,
) -> competition_schemas.TeamComplete:
    school = await competition_cruds.load_school_by_id(school_id, db)
    if school is None:
        raise HTTPException(
            status_code=404,
            detail="School not found in the database",
        ) from None
    sport = await competition_cruds.load_sport_by_id(sport_id, db)
    if sport is None:
        raise HTTPException(
            status_code=404,
            detail="Sport not found in the database",
        ) from None
    team = await competition_cruds.load_team_by_id(team_id, db)
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


@router.get(
    "/competition/sport/{sport_id}/teams",
    response_model=list[competition_schemas.Team],
)
async def get_teams_for_sport(
    sport_id: str,
    db=Depends(get_db),
    user=Depends(
        is_user_a_member_of_extended(
            comptition_group_id=CompetitionGroupType.competition_admin,
        ),
    ),
):
    edition = await competition_cruds.load_active_edition(db)
    if edition is None:
        raise HTTPException(
            status_code=404,
            detail="No active edition found in the database",
        ) from None
    sport = await competition_cruds.load_sport_by_id(sport_id, db)
    if sport is None:
        raise HTTPException(
            status_code=404,
            detail="Sport not found in the database",
        ) from None
    return await competition_cruds.load_all_teams_by_sport_id(sport_id, edition.id, db)


@router.get(
    "/competition/school/{school_id}/sports/{sport_id}/teams",
    response_model=list[competition_schemas.Team],
)
async def get_sport_teams_for_school(
    school_id: str,
    sport_id: str,
    db=Depends(get_db),
):
    edition = await competition_cruds.load_active_edition(db)
    if edition is None:
        raise HTTPException(
            status_code=404,
            detail="No active edition found in the database",
        ) from None
    school = await competition_cruds.load_school_by_id(school_id, db)
    if school is None:
        raise HTTPException(
            status_code=404,
            detail="School not found in the database",
        ) from None
    sport = await competition_cruds.load_sport_by_id(sport_id, db)
    if sport is None:
        raise HTTPException(
            status_code=404,
            detail="Sport not found in the database",
        ) from None
    return await competition_cruds.load_all_teams_by_school_and_sport_ids(
        school_id,
        sport_id,
        edition.id,
        db,
    )


@router.post(
    "/competition/school/{school_id}/sport/{sport_id}/teams",
    status_code=201,
    response_model=competition_schemas.Team,
)
async def create_team(
    school_id: str,
    sport_id: str,
    team_info: competition_schemas.TeamInfo,
    db=Depends(get_db),
    user: schemas_core.CoreUser = Depends(is_user),
):
    edition = await competition_cruds.load_active_edition(db)
    if edition is None:
        raise HTTPException(
            status_code=404,
            detail="No active edition found in the database",
        ) from None
    if (
        user.id != team_info.captain_id
        and CompetitionGroupType.competition_admin.value
        not in [group.id for group in user.groups]
    ):
        raise HTTPException(status_code=403, detail="Unauthorized action") from None
    global_team = await competition_cruds.load_team_by_name(
        team_info.name,
        edition.id,
        db,
    )
    if global_team is not None:
        raise HTTPException(status_code=400, detail="Team already exists") from None
    stored = await competition_cruds.load_all_teams_by_school_and_sport_ids(
        school_id,
        sport_id,
        edition.id,
        db,
    )
    quotas = await competition_cruds.load_quota_by_ids(
        school_id,
        sport_id,
        edition.id,
        db,
    )
    if quotas is not None:
        if len(stored) >= quotas.team_quota:
            raise HTTPException(status_code=400, detail="Team quota reached") from None
    team = competition_schemas.Team(
        id=uuid.uuid4(),
        school_id=school_id,
        sport_id=sport_id,
        name=team_info.name,
        captain_id=team_info.captain_id,
        edition_id=edition.id,
    )
    await competition_cruds.store_team(team, db)


@router.patch("/competition/school/{school_id}/sport/{sport_id}/teams")
async def edit_team(
    school_id: str,
    sport_id: str,
    team_info: competition_schemas.TeamEdit,
    db=Depends(get_db),
    user: schemas_core.CoreUser = Depends(is_user),
):
    stored = await check_team_consistency(
        school_id,
        sport_id,
        team_info.id,
        db,
    )
    if (
        user.id != stored.captain_id
        and CompetitionGroupType.competition_admin.value
        not in [group.id for group in user.groups]
    ):
        raise HTTPException(status_code=403, detail="Unauthorized action") from None
    if team_info.captain_id is not None:
        captain = await cruds_users.get_user_by_id(
            db,
            team_info.captain_id,
        )
        if captain is None:
            raise HTTPException(
                status_code=404,
                detail="Captain user not found",
            ) from None
    stored.model_copy(update=team_info.model_dump())
    await competition_cruds.store_team(stored, db)


@router.delete("/competition/school/{school_id}/sport/{sport_id}/teams/{team_id}")
async def delete_team(
    school_id: str,
    sport_id: str,
    team_id: str,
    db=Depends(get_db),
    user: schemas_core.CoreUser = Depends(is_user),
):
    stored = await check_team_consistency(
        school_id,
        sport_id,
        team_id,
        db,
    )
    if (
        user.id != stored.captain_id
        and CompetitionGroupType.competition_admin.value
        not in [group.id for group in user.groups]
    ):
        raise HTTPException(status_code=403, detail="Unauthorized action") from None
    await competition_cruds.delete_team_by_id(stored.id, db)
