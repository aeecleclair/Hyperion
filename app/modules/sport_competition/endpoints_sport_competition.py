import logging
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.schools import cruds_schools
from app.core.users import cruds_users, schemas_users
from app.dependencies import get_db, is_user
from app.modules.sport_competition import cruds_sport_competition as competition_cruds
from app.modules.sport_competition import (
    schemas_sport_competition as competition_schemas,
)
from app.modules.sport_competition.dependencies_sport_competition import (
    get_current_edition,
    is_user_a_member_of_extended,
)
from app.modules.sport_competition.types_sport_competition import CompetitionGroupType

router = APIRouter(tags=["Sport Competition"])
hyperion_error_logger = logging.getLogger("hyperion.error")


@router.get("/competition/sports", response_model=list[competition_schemas.Sport])
async def get_sports(db: AsyncSession = Depends(get_db)):
    return await competition_cruds.load_all_sports(db)


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
    sport = competition_schemas.Sport(**sport.model_dump(), id=str(uuid4()))
    await competition_cruds.store_sport(sport, db)
    return sport


@router.patch("/competition/sports/{sport_id}")
async def edit_sport(
    sport_id: UUID,
    sport: competition_schemas.SportEdit,
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
    stored.model_copy(update=sport.model_dump())
    await competition_cruds.store_sport(stored, db)
    return stored


@router.delete("/competition/sports/{sport_id}")
async def delete_sport(
    sport_id: UUID,
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
async def get_groups(
    db=Depends(get_db),
    edition: competition_schemas.CompetitionEdition = Depends(get_current_edition),
):
    return await competition_cruds.load_all_groups(edition.id, db)


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
    group = competition_schemas.Group(**group.model_dump(), id=str(uuid4()))
    await competition_cruds.add_group(group, db)
    return group


@router.patch("/competition/groups/{group_id}")
async def edit_group(
    group_id: UUID,
    group: competition_schemas.GroupEdit,
    db=Depends(get_db),
    user=Depends(
        is_user_a_member_of_extended(
            comptition_group_id=CompetitionGroupType.competition_admin,
        ),
    ),
    edition: competition_schemas.CompetitionEdition = Depends(get_current_edition),
):
    stored = await competition_cruds.load_group_by_id(group_id, edition.id, db)
    if stored is None:
        raise HTTPException(status_code=404, detail="Group not found") from None
    await competition_cruds.update_group(group_id, group, db)


@router.delete("/competition/groups/{group_id}")
async def delete_group(
    group_id: UUID,
    db=Depends(get_db),
    user=Depends(
        is_user_a_member_of_extended(
            comptition_group_id=CompetitionGroupType.competition_admin,
        ),
    ),
    edition: competition_schemas.CompetitionEdition = Depends(get_current_edition),
):
    stored = await competition_cruds.load_group_by_id(group_id, edition.id, db)
    if stored is None:
        raise HTTPException(status_code=404, detail="Group not found") from None

    # await competition_cruds.delete_group_membership_by_group_id(group_id, db)

    await competition_cruds.delete_group_by_id(group_id, db)


@router.get(
    "/competition/sports/{sport_id}/quotas",
    response_model=list[competition_schemas.Quota],
)
async def get_quotas_for_sport(
    sport_id: UUID,
    db=Depends(get_db),
    user=Depends(
        is_user_a_member_of_extended(
            comptition_group_id=CompetitionGroupType.competition_admin,
        ),
    ),
    edition: competition_schemas.CompetitionEdition = Depends(get_current_edition),
):
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
    "/competition/schools/{school_id}/quotas",
    response_model=list[competition_schemas.Quota],
)
async def get_quotas_for_school(
    school_id: UUID,
    db=Depends(get_db),
    edition: competition_schemas.CompetitionEdition = Depends(get_current_edition),
):
    school = await competition_cruds.load_school_by_id(school_id, edition.id, db)
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


@router.post(
    "/competition/schools/{school_id}/sports/{sport_id}/quotas",
    status_code=201,
)
async def create_quota(
    school_id: UUID,
    sport_id: UUID,
    quota_info: competition_schemas.QuotaInfo,
    db=Depends(get_db),
    user=Depends(
        is_user_a_member_of_extended(
            comptition_group_id=CompetitionGroupType.competition_admin,
        ),
    ),
    edition: competition_schemas.CompetitionEdition = Depends(get_current_edition),
):
    school = await competition_cruds.load_school_by_id(school_id, edition.id, db)
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


@router.patch("/competition/schools/{school_id}/sports/{sport_id}/quotas")
async def edit_quota(
    school_id: UUID,
    sport_id: UUID,
    quota_info: competition_schemas.QuotaEdit,
    db=Depends(get_db),
    user=Depends(
        is_user_a_member_of_extended(
            comptition_group_id=CompetitionGroupType.competition_admin,
        ),
    ),
    edition: competition_schemas.CompetitionEdition = Depends(get_current_edition),
):
    school = await competition_cruds.load_school_by_id(school_id, edition.id, db)
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


@router.delete("/competition/schools/{school_id}/sports/{sport_id}/quotas")
async def delete_quota(
    school_id: UUID,
    sport_id: UUID,
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
async def get_schools(
    db=Depends(get_db),
    edition: competition_schemas.CompetitionEdition = Depends(get_current_edition),
):
    return await competition_cruds.load_all_schools(edition.id, db)


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
    edition: competition_schemas.CompetitionEdition = Depends(get_current_edition),
):
    core_school = await cruds_schools.get_school_by_id(db, school.school_id)
    if core_school is None:
        raise HTTPException(
            status_code=404,
            detail="School not found in the database",
        ) from None
    stored = await competition_cruds.load_school_by_id(school.school_id, edition.id, db)
    if stored is not None:
        raise HTTPException(
            status_code=400,
            detail="School extension already exists",
        ) from None
    await competition_cruds.add_school(school, db)
    return school


@router.patch("/competition/schools/{school_id}")
async def edit_school(
    school_id: UUID,
    school: competition_schemas.SchoolExtensionEdit,
    db=Depends(get_db),
    user=Depends(
        is_user_a_member_of_extended(
            comptition_group_id=CompetitionGroupType.competition_admin,
        ),
    ),
    edition: competition_schemas.CompetitionEdition = Depends(get_current_edition),
):
    stored = await competition_cruds.load_school_by_id(school_id, edition.id, db)
    if stored is None:
        raise HTTPException(
            status_code=404,
            detail="School not found in the database",
        ) from None
    await competition_cruds.update_school(school_id, school, db)


@router.delete("/competition/schools/{school_id}")
async def delete_school(
    school_id: UUID,
    db=Depends(get_db),
    user=Depends(
        is_user_a_member_of_extended(
            comptition_group_id=CompetitionGroupType.competition_admin,
        ),
    ),
    edition: competition_schemas.CompetitionEdition = Depends(get_current_edition),
):
    stored = await competition_cruds.load_school_by_id(school_id, edition.id, db)
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
    school_id: UUID,
    sport_id: UUID,
    team_id: UUID,
    db: AsyncSession,
    edition: competition_schemas.CompetitionEdition = Depends(get_current_edition),
) -> competition_schemas.TeamComplete:
    school = await competition_cruds.load_school_by_id(school_id, edition.id, db)
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
    "/competition/teams/sports/{sport_id}",
    response_model=list[competition_schemas.Team],
)
async def get_teams_for_sport(
    sport_id: UUID,
    db=Depends(get_db),
    user=Depends(
        is_user_a_member_of_extended(
            comptition_group_id=CompetitionGroupType.competition_admin,
        ),
    ),
    edition: competition_schemas.CompetitionEdition = Depends(get_current_edition),
):
    sport = await competition_cruds.load_sport_by_id(sport_id, db)
    if sport is None:
        raise HTTPException(
            status_code=404,
            detail="Sport not found in the database",
        ) from None
    return await competition_cruds.load_all_teams_by_sport_id(sport_id, edition.id, db)


@router.get(
    "/competition/teams/schools/{school_id}/sports/{sport_id}",
    response_model=list[competition_schemas.Team],
)
async def get_sport_teams_for_school_and_sport(
    school_id: UUID,
    sport_id: UUID,
    db=Depends(get_db),
    edition: competition_schemas.CompetitionEdition = Depends(get_current_edition),
):
    school = await competition_cruds.load_school_by_id(school_id, edition.id, db)
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
    "/competition/teams/schools/{school_id}/sports/{sport_id}",
    status_code=201,
    response_model=competition_schemas.Team,
)
async def create_team(
    school_id: UUID,
    sport_id: UUID,
    team_info: competition_schemas.TeamInfo,
    db=Depends(get_db),
    edition: competition_schemas.CompetitionEdition = Depends(get_current_edition),
    user: schemas_users.CoreUser = Depends(is_user),
):
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
        if len(stored) == quotas.team_quota:
            raise HTTPException(status_code=400, detail="Team quota reached") from None
    team = competition_schemas.Team(
        id=uuid4(),
        school_id=school_id,
        sport_id=sport_id,
        name=team_info.name,
        captain_id=team_info.captain_id,
        edition_id=edition.id,
    )
    await competition_cruds.store_team(team, db)


@router.post("/competition/sports/{sport_id}/join}")
async def join_team(
    sport_id: UUID,
    participant_info: competition_schemas.ParticipantInfo,
    db=Depends(get_db),
    user: schemas_users.CoreUser = Depends(is_user),
    edition: competition_schemas.CompetitionEdition = Depends(get_current_edition),
):
    sport = await competition_cruds.load_sport_by_id(sport_id, db)
    if sport is None:
        raise HTTPException(
            status_code=404,
            detail="Sport not found in the database",
        ) from None
    school_quota = await competition_cruds.load_quota_by_ids(
        user.school_id,
        sport_id,
        edition.id,
        db,
    )
    if school_quota is not None:
        participants = (
            await competition_cruds.load_participants_by_school_and_sport_ids(
                user.school_id,
                sport_id,
                edition.id,
                db,
            )
        )
        if len(participants) == school_quota.participant_quota:
            raise HTTPException(
                status_code=400,
                detail="Participant quota reached",
            ) from None
    if sport.team_size > 1:
        if participant_info.team_id is None:
            raise HTTPException(
                status_code=400,
                detail="Sport declared needs to be played in a team",
            ) from None
        team = await check_team_consistency(
            user.school_id,
            sport_id,
            participant_info.team_id,
            db,
        )
        if (
            not participant_info.substitute
            and len(
                [user for user in team.participants if not user.substitute],
            )
            == sport.team_size
        ):
            raise HTTPException(
                status_code=400,
                detail="Maximum number of players in the team reached",
            ) from None
        if (
            participant_info.substitute
            and len(
                [user for user in team.participants if user.substitute],
            )
            == sport.substitute_max
        ):
            raise HTTPException(
                status_code=400,
                detail="Maximum number of substitutes in the team reached",
            ) from None
    await competition_cruds.store_participant(
        competition_schemas.Participant(
            user_id=user.id,
            sport_id=sport_id,
            edition_id=edition.id,
            **participant_info.__dict__,
        ),
        db,
    )


@router.patch("/competition/teams/{team_id}")
async def edit_team(
    team_id: UUID,
    team_info: competition_schemas.TeamEdit,
    db=Depends(get_db),
    user: schemas_users.CoreUser = Depends(is_user),
):
    stored = await competition_cruds.load_team_by_id(team_id, db)
    if stored is None:
        raise HTTPException(
            status_code=404,
            detail="Team not found in the database",
        ) from None
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


@router.delete("/competition/teams/{team_id}")
async def delete_team(
    team_id: UUID,
    db=Depends(get_db),
    user: schemas_users.CoreUser = Depends(is_user),
):
    stored = await competition_cruds.load_team_by_id(team_id, db)
    if stored is None:
        raise HTTPException(
            status_code=404,
            detail="Team not found in the database",
        ) from None
    if (
        user.id != stored.captain_id
        and CompetitionGroupType.competition_admin.value
        not in [group.id for group in user.groups]
    ):
        raise HTTPException(status_code=403, detail="Unauthorized action") from None
    await competition_cruds.delete_team_by_id(stored.id, db)


@router.get(
    "/competition/sports/{sport_id}/matches",
    response_model=list[competition_schemas.Match],
)
async def get_matches_for_sport_and_edition(
    sport_id: UUID,
    edition: competition_schemas.CompetitionEdition = Depends(get_current_edition),
    db=Depends(get_db),
):
    sport = await competition_cruds.load_sport_by_id(sport_id, db)
    if sport is None:
        raise HTTPException(
            status_code=404,
            detail="Sport not found in the database",
        ) from None
    return await competition_cruds.load_all_matches_by_sport_id(
        sport_id,
        edition.id,
        db,
    )


@router.get(
    "/competition/schools/{school_id}/matches",
    response_model=list[competition_schemas.Match],
)
async def get_matches_for_school_sport_and_edition(
    school_id: UUID,
    sport_id: UUID,
    edition: competition_schemas.CompetitionEdition = Depends(get_current_edition),
    db=Depends(get_db),
):
    school = await competition_cruds.load_school_by_id(school_id, edition.id, db)
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
    return await competition_cruds.load_all_matches_by_school_id(
        school_id,
        edition.id,
        db,
    )


def check_match_consistency(
    sport_id: UUID,
    match_info: competition_schemas.MatchBase,
    team1: competition_schemas.TeamComplete,
    team2: competition_schemas.TeamComplete,
    edition: competition_schemas.CompetitionEdition,
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


@router.post(
    "/competition/sports/{sport_id}/matches",
    status_code=201,
    response_model=competition_schemas.Match,
)
async def create_match(
    sport_id: UUID,
    match_info: competition_schemas.MatchBase,
    db=Depends(get_db),
    user: schemas_users.CoreUser = Depends(is_user),
    edition: competition_schemas.CompetitionEdition = Depends(get_current_edition),
):
    sport = await competition_cruds.load_sport_by_id(sport_id, db)
    if sport is None:
        raise HTTPException(
            status_code=404,
            detail="Sport not found in the database",
        ) from None
    team1 = await competition_cruds.load_team_by_id(match_info.team1_id, db)
    if team1 is None:
        raise HTTPException(
            status_code=404,
            detail="Team 1 not found in the database",
        ) from None
    team2 = await competition_cruds.load_team_by_id(match_info.team2_id, db)
    if team2 is None:
        raise HTTPException(
            status_code=404,
            detail="Team 2 not found in the database",
        ) from None

    check_match_consistency(sport_id, match_info, team1, team2, edition)

    match = competition_schemas.Match(
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
    await competition_cruds.store_match(match, db)


@router.patch("/competition/matches/{match_id}")
async def edit_match(
    match_id: UUID,
    match_info: competition_schemas.MatchBase,
    db=Depends(get_db),
    user: schemas_users.CoreUser = Depends(is_user),
    edition: competition_schemas.CompetitionEdition = Depends(get_current_edition),
):
    match = await competition_cruds.load_match_by_id(match_id, db)
    if match is None:
        raise HTTPException(
            status_code=404,
            detail="Match not found in the database",
        ) from None
    team1 = await competition_cruds.load_team_by_id(match_info.team1_id, db)
    if team1 is None:
        raise HTTPException(
            status_code=404,
            detail="Team 1 not found in the database",
        ) from None
    team2 = await competition_cruds.load_team_by_id(match_info.team2_id, db)
    if team2 is None:
        raise HTTPException(
            status_code=404,
            detail="Team 2 not found in the database",
        ) from None

    check_match_consistency(match.sport_id, match_info, team1, team2, edition)

    match.model_copy(update=match_info.model_dump())
    await competition_cruds.store_match(match, db)


@router.delete("/competition/matches/{match_id}")
async def delete_match(
    match_id: UUID,
    db=Depends(get_db),
    user: schemas_users.CoreUser = Depends(is_user),
):
    match = await competition_cruds.load_match_by_id(match_id, db)
    if match is None:
        raise HTTPException(
            status_code=404,
            detail="Match not found in the database",
        ) from None
    await competition_cruds.delete_match_by_id(match_id, db)
