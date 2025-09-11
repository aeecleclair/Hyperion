import logging
from uuid import UUID

from sqlalchemy import and_, delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.schools import models_schools
from app.modules.sport_competition import (
    models_sport_competition,
    schemas_sport_competition,
)
from app.modules.sport_competition.types_sport_competition import (
    CompetitionGroupType,
)
from app.modules.sport_competition.utils_sport_competition import (
    competition_user_model_to_schema,
    match_model_to_schema,
    participant_complete_model_to_schema,
    school_extension_model_to_schema,
    school_extension_model_to_schema_complete,
    team_model_to_schema,
)

logger = logging.getLogger("hyperion.error")


async def load_memberships_by_competition_group(
    group: CompetitionGroupType,
    edition_id: UUID,
    db: AsyncSession,
) -> list[schemas_sport_competition.UserGroupMembership]:
    membership = (
        (
            await db.execute(
                select(models_sport_competition.CompetitionGroupMembership).where(
                    models_sport_competition.CompetitionGroupMembership.group == group,
                    models_sport_competition.CompetitionGroupMembership.edition_id
                    == edition_id,
                ),
            )
        )
        .scalars()
        .all()
    )
    return [
        schemas_sport_competition.UserGroupMembership(
            user_id=membership.user_id,
            group=membership.group,
            edition_id=membership.edition_id,
        )
        for membership in membership
    ]


async def load_user_competition_groups_memberships(
    user_id: str,
    edition_id: UUID,
    db: AsyncSession,
) -> list[schemas_sport_competition.UserGroupMembership]:
    memberships = (
        (
            await db.execute(
                select(models_sport_competition.CompetitionGroupMembership).where(
                    models_sport_competition.CompetitionGroupMembership.user_id
                    == user_id,
                    models_sport_competition.CompetitionGroupMembership.edition_id
                    == edition_id,
                ),
            )
        )
        .scalars()
        .all()
    )
    return [
        schemas_sport_competition.UserGroupMembership(
            user_id=membership.user_id,
            group=membership.group,
            edition_id=membership.edition_id,
        )
        for membership in memberships
    ]


async def add_user_to_group(
    user_id: str,
    group: CompetitionGroupType,
    edition_id: UUID,
    db: AsyncSession,
) -> None:
    db.add(
        models_sport_competition.CompetitionGroupMembership(
            user_id=user_id,
            group=group,
            edition_id=edition_id,
        ),
    )
    await db.flush()


async def remove_user_from_group(
    user_id: str,
    group: CompetitionGroupType,
    edition_id: UUID,
    db: AsyncSession,
) -> None:
    await db.delete(
        models_sport_competition.CompetitionGroupMembership(
            user_id=user_id,
            group=group,
            edition_id=edition_id,
        ),
    )
    await db.flush()


async def load_all_competition_users(
    edition_id: UUID,
    db: AsyncSession,
) -> list[schemas_sport_competition.CompetitionUser]:
    competition_users = await db.execute(
        select(models_sport_competition.CompetitionUser).where(
            models_sport_competition.CompetitionUser.edition_id == edition_id,
        ),
    )
    return [
        competition_user_model_to_schema(competition_user)
        for competition_user in competition_users.scalars().all()
    ]


async def load_competition_user_by_id(
    user_id: str,
    edition_id: UUID,
    db: AsyncSession,
) -> schemas_sport_competition.CompetitionUser | None:
    user = (
        (
            await db.execute(
                select(models_sport_competition.CompetitionUser).where(
                    models_sport_competition.CompetitionUser.user_id == user_id,
                    models_sport_competition.CompetitionUser.edition_id == edition_id,
                ),
            )
        )
        .scalars()
        .first()
    )
    return competition_user_model_to_schema(user) if user else None


async def add_competition_user(
    user: schemas_sport_competition.CompetitionUserSimple,
    db: AsyncSession,
):
    db.add(
        models_sport_competition.CompetitionUser(
            user_id=user.user_id,
            edition_id=user.edition_id,
            sport_category=user.sport_category,
            is_athlete=user.is_athlete,
            is_cameraman=user.is_cameraman,
            is_pompom=user.is_pompom,
            is_fanfare=user.is_fanfare,
            is_volunteer=user.is_volunteer,
            validated=user.validated,
            created_at=user.created_at,
        ),
    )
    await db.flush()


async def update_competition_user(
    user_id: str,
    edition_id: UUID,
    user: schemas_sport_competition.CompetitionUserEdit,
    db: AsyncSession,
):
    await db.execute(
        update(models_sport_competition.CompetitionUser)
        .where(
            models_sport_competition.CompetitionUser.user_id == user_id,
            models_sport_competition.CompetitionUser.edition_id == edition_id,
        )
        .values(**user.model_dump(exclude_unset=True)),
    )
    await db.flush()


async def add_school(
    school: schemas_sport_competition.SchoolExtensionBase,
    db: AsyncSession,
):
    db.add(
        models_sport_competition.SchoolExtension(
            school_id=school.school_id,
            from_lyon=school.from_lyon,
            active=school.active,
            inscription_enabled=school.inscription_enabled,
        ),
    )
    await db.flush()


async def update_school(
    school_id: UUID,
    school: schemas_sport_competition.SchoolExtensionEdit,
    db: AsyncSession,
):
    await db.execute(
        update(models_sport_competition.SchoolExtension)
        .where(models_sport_competition.SchoolExtension.school_id == school_id)
        .values(**school.model_dump(exclude_unset=True)),
    )
    await db.flush()


async def delete_school_by_id(
    school_id: UUID,
    db: AsyncSession,
):
    await db.execute(
        delete(models_sport_competition.SchoolExtension).where(
            models_sport_competition.SchoolExtension.school_id == school_id,
        ),
    )
    await db.flush()


async def load_school_base_by_id(
    school_id: UUID,
    db: AsyncSession,
) -> schemas_sport_competition.SchoolExtensionBase | None:
    school = await db.get(models_sport_competition.SchoolExtension, school_id)
    return (
        schemas_sport_competition.SchoolExtensionBase(
            school_id=school.school_id,
            from_lyon=school.from_lyon,
            active=school.active,
        )
        if school
        else None
    )


async def load_school_by_id(
    school_id: UUID,
    edition_id: UUID,
    db: AsyncSession,
) -> schemas_sport_competition.SchoolExtensionComplete | None:
    school_extension = (
        (
            await db.execute(
                select(models_sport_competition.SchoolExtension)
                .join(
                    models_sport_competition.SchoolGeneralQuota,
                    and_(
                        models_sport_competition.SchoolExtension.school_id
                        == models_sport_competition.SchoolGeneralQuota.school_id,
                        models_sport_competition.SchoolGeneralQuota.edition_id
                        == edition_id,
                    ),
                    isouter=True,
                )
                .where(
                    models_sport_competition.SchoolExtension.school_id == school_id,
                )
                .options(
                    selectinload(models_sport_competition.SchoolExtension.school),
                    selectinload(
                        models_sport_competition.SchoolExtension.general_quota,
                    ),
                    selectinload(
                        models_sport_competition.SchoolExtension.product_quotas,
                    ),
                ),
            )
        )
        .scalars()
        .first()
    )
    return (
        school_extension_model_to_schema_complete(school_extension)
        if school_extension
        else None
    )


async def load_school_by_name(
    name: str,
    edition_id: UUID,
    db: AsyncSession,
) -> schemas_sport_competition.SchoolExtensionBase | None:
    school_extension = (
        (
            await db.execute(
                select(models_sport_competition.SchoolExtension)
                .join(
                    models_schools.CoreSchool,
                )
                .where(
                    models_schools.CoreSchool.name == name,
                ),
            )
        )
        .scalars()
        .first()
    )
    return (
        schemas_sport_competition.SchoolExtensionBase(
            school_id=school_extension.school_id,
            from_lyon=school_extension.from_lyon,
            active=school_extension.active,
            inscription_enabled=school_extension.inscription_enabled,
        )
        if school_extension
        else None
    )


async def load_all_schools(
    edition_id: UUID,
    db: AsyncSession,
) -> list[schemas_sport_competition.SchoolExtension]:
    school_extensions = await db.execute(
        select(models_sport_competition.SchoolExtension),
    )
    return [
        school_extension_model_to_schema(school_extension)
        for school_extension in school_extensions.scalars().all()
    ]


async def add_participant(
    participant: schemas_sport_competition.Participant,
    db: AsyncSession,
):
    db.add(
        models_sport_competition.CompetitionParticipant(
            user_id=participant.user_id,
            sport_id=participant.sport_id,
            edition_id=participant.edition_id,
            team_id=participant.team_id,
            school_id=participant.school_id,
            substitute=participant.substitute,
            license=participant.license,
        ),
    )
    await db.flush()


async def update_participant(
    user_id: str,
    sport_id: UUID,
    edition_id: UUID,
    participant: schemas_sport_competition.ParticipantEdit,
    db: AsyncSession,
):
    await db.execute(
        update(models_sport_competition.CompetitionParticipant)
        .where(
            and_(
                models_sport_competition.CompetitionParticipant.user_id == user_id,
                models_sport_competition.CompetitionParticipant.sport_id == sport_id,
                models_sport_competition.CompetitionParticipant.edition_id
                == edition_id,
            ),
        )
        .values(**participant.model_dump(exclude_unset=True)),
    )
    await db.flush()


async def validate_participant(
    user_id: str,
    edition_id: UUID,
    db: AsyncSession,
):
    await db.execute(
        update(models_sport_competition.CompetitionUser)
        .where(
            and_(
                models_sport_competition.CompetitionUser.user_id == user_id,
                models_sport_competition.CompetitionUser.edition_id == edition_id,
            ),
        )
        .values(validated=True),
    )
    await db.flush()


async def delete_participant_by_ids(
    user_id: str,
    sport_id: UUID,
    edition_id: UUID,
    db: AsyncSession,
):
    await db.execute(
        delete(models_sport_competition.CompetitionParticipant).where(
            models_sport_competition.CompetitionParticipant.user_id == user_id,
            models_sport_competition.CompetitionParticipant.sport_id == sport_id,
            models_sport_competition.CompetitionParticipant.edition_id == edition_id,
        ),
    )
    await db.flush()


async def load_participant_by_ids(
    user_id: str,
    sport_id: UUID,
    edition_id: UUID,
    db: AsyncSession,
) -> schemas_sport_competition.ParticipantComplete | None:
    participant = (
        (
            await db.execute(
                select(models_sport_competition.CompetitionParticipant)
                .where(
                    models_sport_competition.CompetitionParticipant.user_id == user_id,
                    models_sport_competition.CompetitionParticipant.sport_id
                    == sport_id,
                    models_sport_competition.CompetitionParticipant.edition_id
                    == edition_id,
                )
                .options(
                    selectinload(models_sport_competition.CompetitionUser.user),
                ),
            )
        )
        .scalars()
        .first()
    )
    return participant_complete_model_to_schema(participant) if participant else None


async def load_all_participants(
    edition_id: UUID,
    db: AsyncSession,
) -> list[schemas_sport_competition.ParticipantComplete]:
    participants = await db.execute(
        select(models_sport_competition.CompetitionParticipant)
        .where(
            models_sport_competition.CompetitionParticipant.edition_id == edition_id,
        )
        .options(
            selectinload(models_sport_competition.CompetitionUser.user),
        ),
    )
    return [
        participant_complete_model_to_schema(participant)
        for participant in participants.scalars().all()
    ]


async def load_participants_by_school_id(
    school_id: UUID,
    edition_id: UUID,
    db: AsyncSession,
) -> list[schemas_sport_competition.ParticipantComplete]:
    participants = (
        (
            await db.execute(
                select(models_sport_competition.CompetitionParticipant)
                .where(
                    models_sport_competition.CompetitionParticipant.edition_id
                    == edition_id,
                    models_sport_competition.CompetitionParticipant.school_id
                    == school_id,
                )
                .options(selectinload(models_sport_competition.CompetitionUser.user)),
            )
        )
        .scalars()
        .all()
    )
    return [
        participant_complete_model_to_schema(participant)
        for participant in participants
    ]


async def load_participants_by_sport_id(
    sport_id: UUID,
    edition_id: UUID,
    db: AsyncSession,
) -> list[schemas_sport_competition.ParticipantComplete]:
    participants = (
        (
            await db.execute(
                select(models_sport_competition.CompetitionParticipant)
                .where(
                    models_sport_competition.CompetitionParticipant.sport_id
                    == sport_id,
                    models_sport_competition.CompetitionParticipant.edition_id
                    == edition_id,
                )
                .options(
                    selectinload(models_sport_competition.CompetitionUser.user),
                ),
            )
        )
        .scalars()
        .all()
    )
    return [
        participant_complete_model_to_schema(participant)
        for participant in participants
    ]


async def load_participants_by_school_and_sport_ids(
    school_id: UUID,
    sport_id: UUID,
    edition_id: UUID,
    db: AsyncSession,
) -> list[schemas_sport_competition.ParticipantComplete]:
    participants = (
        (
            await db.execute(
                select(models_sport_competition.CompetitionParticipant)
                .where(
                    models_sport_competition.CompetitionParticipant.sport_id
                    == sport_id,
                    models_sport_competition.CompetitionParticipant.edition_id
                    == edition_id,
                    models_sport_competition.CompetitionParticipant.school_id
                    == school_id,
                )
                .options(
                    selectinload(models_sport_competition.CompetitionUser.user),
                ),
            )
        )
        .scalars()
        .all()
    )
    return [
        participant_complete_model_to_schema(participant)
        for participant in participants
    ]


async def load_validated_participants_number_by_school_and_sport_ids(
    school_id: UUID,
    sport_id: UUID,
    edition_id: UUID,
    db: AsyncSession,
) -> int:
    """
    Load the number of validated participants for a given school and sport in a specific edition.
    """
    result = await db.execute(
        select(func.count()).where(
            models_sport_competition.CompetitionParticipant.sport_id == sport_id,
            models_sport_competition.CompetitionParticipant.edition_id == edition_id,
            models_sport_competition.CompetitionParticipant.school_id == school_id,
            models_sport_competition.CompetitionUser.validated,
        ),
    )
    return result.scalar() or 0


async def get_school_general_quota(
    school_id: UUID,
    edition_id: UUID,
    db: AsyncSession,
) -> schemas_sport_competition.SchoolGeneralQuota | None:
    quota = await db.get(
        models_sport_competition.SchoolGeneralQuota,
        (school_id, edition_id),
    )
    return (
        schemas_sport_competition.SchoolGeneralQuota(
            school_id=quota.school_id,
            edition_id=quota.edition_id,
            athlete_quota=quota.athlete_quota,
            cameraman_quota=quota.cameraman_quota,
            pompom_quota=quota.pompom_quota,
            fanfare_quota=quota.fanfare_quota,
        )
        if quota
        else None
    )


async def add_school_general_quota(
    quota: schemas_sport_competition.SchoolGeneralQuota,
    db: AsyncSession,
):
    db.add(models_sport_competition.SchoolGeneralQuota(**quota.model_dump()))
    await db.flush()


async def update_school_general_quota(
    school_id: UUID,
    edition_id: UUID,
    quota: schemas_sport_competition.SchoolGeneralQuotaBase,
    db: AsyncSession,
):
    await db.execute(
        update(models_sport_competition.SchoolGeneralQuota)
        .where(
            models_sport_competition.SchoolGeneralQuota.school_id == school_id,
            models_sport_competition.SchoolGeneralQuota.edition_id == edition_id,
        )
        .values(**quota.model_dump(exclude_unset=True)),
    )
    await db.flush()


async def delete_school_general_quota_by_ids(
    school_id: UUID,
    edition_id: UUID,
    db: AsyncSession,
):
    await db.execute(
        delete(models_sport_competition.SchoolGeneralQuota).where(
            models_sport_competition.SchoolGeneralQuota.school_id == school_id,
            models_sport_competition.SchoolGeneralQuota.edition_id == edition_id,
        ),
    )
    await db.flush()


async def add_sport_quota(
    quota: schemas_sport_competition.Quota,
    db: AsyncSession,
):
    db.add(models_sport_competition.SchoolSportQuota(**quota.model_dump()))
    await db.flush()


async def update_sport_quota(
    school_id: UUID,
    sport_id: UUID,
    edition_id: UUID,
    quota: schemas_sport_competition.QuotaEdit,
    db: AsyncSession,
):
    await db.execute(
        update(models_sport_competition.SchoolSportQuota)
        .where(
            models_sport_competition.SchoolSportQuota.school_id == school_id,
            models_sport_competition.SchoolSportQuota.sport_id == sport_id,
            models_sport_competition.SchoolSportQuota.edition_id == edition_id,
        )
        .values(**quota.model_dump(exclude_unset=True)),
    )
    await db.flush()


async def delete_sport_quota_by_ids(
    school_id: UUID,
    sport_id: UUID,
    edition_id: UUID,
    db: AsyncSession,
):
    await db.execute(
        delete(models_sport_competition.SchoolSportQuota).where(
            models_sport_competition.SchoolSportQuota.school_id == school_id,
            models_sport_competition.SchoolSportQuota.sport_id == sport_id,
            models_sport_competition.SchoolSportQuota.edition_id == edition_id,
        ),
    )
    await db.flush()


async def load_sport_quota_by_ids(
    school_id: UUID,
    sport_id: UUID,
    edition_id: UUID,
    db: AsyncSession,
) -> schemas_sport_competition.Quota | None:
    quota = await db.get(
        models_sport_competition.SchoolSportQuota,
        (school_id, sport_id, edition_id),
    )
    return (
        schemas_sport_competition.Quota(
            school_id=quota.school_id,
            sport_id=quota.sport_id,
            edition_id=quota.edition_id,
            participant_quota=quota.participant_quota,
            team_quota=quota.team_quota,
        )
        if quota
        else None
    )


async def load_all_sport_quotas_by_school_id(
    school_id: UUID,
    edition_id: UUID,
    db: AsyncSession,
) -> list[schemas_sport_competition.Quota]:
    quotas = await db.execute(
        select(models_sport_competition.SchoolSportQuota).where(
            models_sport_competition.SchoolSportQuota.school_id == school_id,
            models_sport_competition.SchoolSportQuota.edition_id == edition_id,
        ),
    )
    return [
        schemas_sport_competition.Quota(
            school_id=quota.school_id,
            sport_id=quota.sport_id,
            edition_id=quota.edition_id,
            participant_quota=quota.participant_quota,
            team_quota=quota.team_quota,
        )
        for quota in quotas.scalars().all()
    ]


async def load_all_sport_quotas_by_sport_id(
    sport_id: UUID,
    edition_id: UUID,
    db: AsyncSession,
) -> list[schemas_sport_competition.Quota]:
    quotas = await db.execute(
        select(models_sport_competition.SchoolSportQuota).where(
            models_sport_competition.SchoolSportQuota.sport_id == sport_id,
            models_sport_competition.SchoolSportQuota.edition_id == edition_id,
        ),
    )
    return [
        schemas_sport_competition.Quota(
            school_id=quota.school_id,
            sport_id=quota.sport_id,
            edition_id=quota.edition_id,
            participant_quota=quota.participant_quota,
            team_quota=quota.team_quota,
        )
        for quota in quotas.scalars().all()
    ]


async def add_sport(
    sport: schemas_sport_competition.Sport,
    db: AsyncSession,
):
    db.add(models_sport_competition.Sport(**sport.model_dump()))
    await db.flush()


async def update_sport(
    sport_id: UUID,
    sport: schemas_sport_competition.SportEdit,
    db: AsyncSession,
):
    await db.execute(
        update(models_sport_competition.Sport)
        .where(models_sport_competition.Sport.id == sport_id)
        .values(**sport.model_dump(exclude_unset=True)),
    )
    await db.flush()


async def delete_sport_by_id(
    sport_id: UUID,
    db: AsyncSession,
):
    await db.execute(
        delete(models_sport_competition.Sport).where(
            models_sport_competition.Sport.id == sport_id,
        ),
    )
    await db.flush()


async def load_sport_by_id(
    sport_id: UUID,
    db: AsyncSession,
) -> schemas_sport_competition.Sport | None:
    sport = await db.get(models_sport_competition.Sport, sport_id)
    return (
        schemas_sport_competition.Sport(
            id=sport.id,
            name=sport.name,
            team_size=sport.team_size,
            substitute_max=sport.substitute_max,
            sport_category=sport.sport_category,
            active=sport.active,
        )
        if sport
        else None
    )


async def load_sport_by_name(
    name: str,
    db: AsyncSession,
) -> schemas_sport_competition.Sport | None:
    sport = (
        (
            await db.execute(
                select(models_sport_competition.Sport).where(
                    models_sport_competition.Sport.name == name,
                ),
            )
        )
        .scalars()
        .first()
    )
    return (
        schemas_sport_competition.Sport(
            id=sport.id,
            name=sport.name,
            team_size=sport.team_size,
            substitute_max=sport.substitute_max,
            sport_category=sport.sport_category,
            active=sport.active,
        )
        if sport
        else None
    )


async def load_all_sports(
    db: AsyncSession,
) -> list[schemas_sport_competition.Sport]:
    sports = await db.execute(select(models_sport_competition.Sport))
    return [
        schemas_sport_competition.Sport(
            id=sport.id,
            name=sport.name,
            team_size=sport.team_size,
            substitute_max=sport.substitute_max,
            sport_category=sport.sport_category,
            active=sport.active,
        )
        for sport in sports.scalars().all()
    ]


async def add_team(
    team: schemas_sport_competition.Team,
    db: AsyncSession,
):
    db.add(models_sport_competition.CompetitionTeam(**team.model_dump()))
    await db.flush()


async def update_team(
    team_id: UUID,
    team: schemas_sport_competition.TeamEdit,
    db: AsyncSession,
):
    await db.execute(
        update(models_sport_competition.CompetitionTeam)
        .where(models_sport_competition.CompetitionTeam.id == team_id)
        .values(**team.model_dump(exclude_unset=True)),
    )
    await db.flush()


async def delete_team_by_id(
    team_id: UUID,
    db: AsyncSession,
):
    await db.execute(
        delete(models_sport_competition.CompetitionTeam).where(
            models_sport_competition.CompetitionTeam.id == team_id,
        ),
    )
    await db.flush()


async def load_team_by_id(
    team_id,
    db: AsyncSession,
) -> schemas_sport_competition.TeamComplete | None:
    team = (
        (
            await db.execute(
                select(models_sport_competition.CompetitionTeam)
                .where(models_sport_competition.CompetitionTeam.id == team_id)
                .options(
                    selectinload(models_sport_competition.CompetitionTeam.participants),
                    selectinload(models_sport_competition.CompetitionParticipant.user),
                ),
            )
        )
        .scalars()
        .first()
    )
    return team_model_to_schema(team) if team else None


async def load_team_by_name(
    name: str,
    edition_id: UUID,
    db: AsyncSession,
) -> schemas_sport_competition.TeamComplete | None:
    team = (
        (
            await db.execute(
                select(models_sport_competition.CompetitionTeam).where(
                    models_sport_competition.CompetitionTeam.name == name,
                    models_sport_competition.CompetitionTeam.edition_id == edition_id,
                ),
            )
        )
        .scalars()
        .first()
    )
    return (
        schemas_sport_competition.TeamComplete(
            name=team.name,
            school_id=team.school_id,
            sport_id=team.sport_id,
            edition_id=team.edition_id,
            captain_id=team.captain_id,
            id=team.id,
            created_at=team.created_at,
            participants=[],
        )
        if team
        else None
    )


async def load_all_teams_by_sport_id(
    sport_id: UUID,
    edition_id: UUID,
    db: AsyncSession,
) -> list[schemas_sport_competition.TeamComplete]:
    db_teams = await db.execute(
        select(models_sport_competition.CompetitionTeam)
        .where(
            models_sport_competition.CompetitionTeam.sport_id == sport_id,
            models_sport_competition.CompetitionTeam.edition_id == edition_id,
        )
        .options(
            selectinload(models_sport_competition.CompetitionTeam.participants),
        ),
    )
    return [team_model_to_schema(team) for team in db_teams.scalars().all()]


async def load_all_teams_by_school_id(
    school_id: UUID,
    edition_id: UUID,
    db: AsyncSession,
) -> list[schemas_sport_competition.TeamComplete]:
    teams = await db.execute(
        select(models_sport_competition.CompetitionTeam)
        .where(
            models_sport_competition.CompetitionTeam.school_id == school_id,
            models_sport_competition.CompetitionTeam.edition_id == edition_id,
        )
        .options(
            selectinload(models_sport_competition.CompetitionTeam.participants),
        ),
    )
    return [team_model_to_schema(team) for team in teams.scalars().all()]


async def load_all_teams_by_school_and_sport_ids(
    school_id: UUID,
    team_id: UUID,
    edition_id: UUID,
    db: AsyncSession,
) -> list[schemas_sport_competition.TeamComplete]:
    teams = await db.execute(
        select(models_sport_competition.CompetitionTeam)
        .where(
            models_sport_competition.CompetitionTeam.school_id == school_id,
            models_sport_competition.CompetitionTeam.sport_id == team_id,
            models_sport_competition.CompetitionTeam.edition_id == edition_id,
        )
        .options(
            selectinload(models_sport_competition.CompetitionTeam.participants),
        ),
    )
    return [team_model_to_schema(team) for team in teams.scalars().all()]


async def count_teams_by_school_and_sport_ids(
    school_id: UUID,
    sport_id: UUID,
    edition_id: UUID,
    db: AsyncSession,
) -> int:
    """
    Count the number of teams for a given school and sport in a specific edition.
    """
    result = await db.execute(
        select(func.count())
        .where(
            models_sport_competition.CompetitionTeam.school_id == school_id,
            models_sport_competition.CompetitionTeam.sport_id == sport_id,
            models_sport_competition.CompetitionTeam.edition_id == edition_id,
        )
        .with_for_update(),
    )
    return result.scalar() or 0


async def add_edition(
    edition: schemas_sport_competition.CompetitionEdition,
    db: AsyncSession,
):
    db.add(models_sport_competition.CompetitionEdition(**edition.model_dump()))
    await db.flush()


async def update_edition(
    edition_id: UUID,
    edition: schemas_sport_competition.CompetitionEditionEdit,
    db: AsyncSession,
):
    await db.execute(
        update(models_sport_competition.CompetitionEdition)
        .where(models_sport_competition.CompetitionEdition.id == edition_id)
        .values(**edition.model_dump(exclude_unset=True)),
    )
    await db.flush()


async def set_active_edition(
    edition_id: UUID,
    db: AsyncSession,
):
    # Deactivate all other editions
    await db.execute(
        update(models_sport_competition.CompetitionEdition)
        .where(models_sport_competition.CompetitionEdition.active)
        .values(active=False),
    )
    # Activate the specified edition
    await db.execute(
        update(models_sport_competition.CompetitionEdition)
        .where(models_sport_competition.CompetitionEdition.id == edition_id)
        .values(active=True),
    )
    await db.flush()


async def patch_edition_inscription(
    edition_id: UUID,
    enable: bool,
    db: AsyncSession,
):
    await db.execute(
        update(models_sport_competition.CompetitionEdition)
        .where(models_sport_competition.CompetitionEdition.id == edition_id)
        .values(inscription_enabled=enable),
    )
    await db.execute(
        update(models_sport_competition.SchoolExtension)
        .where(models_sport_competition.SchoolExtension.active)
        .values(inscription_enabled=enable),
    )
    await db.flush()


async def delete_edition_by_id(
    edition_id: UUID,
    db: AsyncSession,
):
    await db.execute(
        delete(models_sport_competition.CompetitionEdition).where(
            models_sport_competition.CompetitionEdition.id == edition_id,
        ),
    )
    await db.flush()


async def load_edition_by_id(
    edition_id,
    db: AsyncSession,
) -> schemas_sport_competition.CompetitionEdition | None:
    edition = await db.get(models_sport_competition.CompetitionEdition, edition_id)
    return (
        schemas_sport_competition.CompetitionEdition(
            id=edition.id,
            name=edition.name,
            year=edition.year,
            start_date=edition.start_date,
            end_date=edition.end_date,
            active=edition.active,
            inscription_enabled=edition.inscription_enabled,
        )
        if edition
        else None
    )


async def load_edition_by_name(
    name: str,
    db: AsyncSession,
) -> schemas_sport_competition.CompetitionEdition | None:
    edition = (
        (
            await db.execute(
                select(models_sport_competition.CompetitionEdition).where(
                    models_sport_competition.CompetitionEdition.name == name,
                ),
            )
        )
        .scalars()
        .first()
    )
    return (
        schemas_sport_competition.CompetitionEdition(
            id=edition.id,
            name=edition.name,
            year=edition.year,
            start_date=edition.start_date,
            end_date=edition.end_date,
            active=edition.active,
            inscription_enabled=edition.inscription_enabled,
        )
        if edition
        else None
    )


async def load_active_edition(
    db: AsyncSession,
) -> schemas_sport_competition.CompetitionEdition | None:
    edition = (
        (
            await db.execute(
                select(models_sport_competition.CompetitionEdition).where(
                    models_sport_competition.CompetitionEdition.active,
                ),
            )
        )
        .scalars()
        .first()
    )
    return (
        schemas_sport_competition.CompetitionEdition(
            id=edition.id,
            name=edition.name,
            year=edition.year,
            start_date=edition.start_date,
            end_date=edition.end_date,
            active=edition.active,
            inscription_enabled=edition.inscription_enabled,
        )
        if edition
        else None
    )


async def load_all_editions(
    db: AsyncSession,
) -> list[schemas_sport_competition.CompetitionEdition]:
    editions = await db.execute(select(models_sport_competition.CompetitionEdition))
    return [
        schemas_sport_competition.CompetitionEdition(
            id=edition.id,
            name=edition.name,
            year=edition.year,
            start_date=edition.start_date,
            end_date=edition.end_date,
            active=edition.active,
            inscription_enabled=edition.inscription_enabled,
        )
        for edition in editions.scalars().all()
    ]


async def add_match(
    match: schemas_sport_competition.Match,
    db: AsyncSession,
):
    db.add(models_sport_competition.Match(**match.model_dump()))
    await db.flush()


async def update_match(
    match_id: UUID,
    match: schemas_sport_competition.MatchEdit,
    db: AsyncSession,
):
    await db.execute(
        update(models_sport_competition.Match)
        .where(models_sport_competition.Match.id == match_id)
        .values(**match.model_dump(exclude_unset=True)),
    )
    await db.flush()


async def delete_match_by_id(
    match_id: UUID,
    db: AsyncSession,
):
    await db.execute(
        delete(models_sport_competition.Match).where(
            models_sport_competition.Match.id == match_id,
        ),
    )
    await db.flush()


async def load_match_by_id(
    match_id,
    db: AsyncSession,
) -> schemas_sport_competition.Match | None:
    match = await db.get(models_sport_competition.Match, match_id)
    return match_model_to_schema(match) if match else None


async def load_all_matches_by_sport_id(
    sport_id: UUID,
    edition_id: UUID,
    db: AsyncSession,
) -> list[schemas_sport_competition.Match]:
    matches = await db.execute(
        select(models_sport_competition.Match)
        .where(
            models_sport_competition.Match.sport_id == sport_id,
            models_sport_competition.Match.edition_id == edition_id,
        )
        .options(
            selectinload(models_sport_competition.Match.team1),
            selectinload(models_sport_competition.Match.team2),
        ),
    )

    return [match_model_to_schema(match) for match in matches.scalars().all()]


async def load_all_matches_by_school_id(
    school_id: UUID,
    edition_id: UUID,
    db: AsyncSession,
) -> list[schemas_sport_competition.Match]:
    matches = await db.execute(
        select(models_sport_competition.Match)
        .where(
            models_sport_competition.Match.edition_id == edition_id,
            (
                models_sport_competition.Match.team1_id.in_(
                    select(models_sport_competition.CompetitionTeam.id).where(
                        models_sport_competition.CompetitionTeam.school_id == school_id,
                    ),
                )
                | models_sport_competition.Match.team2_id.in_(
                    select(models_sport_competition.CompetitionTeam.id).where(
                        models_sport_competition.CompetitionTeam.school_id == school_id,
                    ),
                )
            ),
        )
        .options(
            selectinload(models_sport_competition.Match.team1),
            selectinload(models_sport_competition.Match.team2),
        ),
    )

    return [match_model_to_schema(match) for match in matches.scalars().all()]


async def load_match_by_teams_ids(
    team1_id: UUID,
    team2_id: UUID,
    db: AsyncSession,
) -> schemas_sport_competition.Match | None:
    match = (
        (
            await db.execute(
                select(models_sport_competition.Match)
                .where(
                    and_(
                        models_sport_competition.Match.team1_id == team1_id,
                        models_sport_competition.Match.team2_id == team2_id,
                    )
                    | and_(
                        (models_sport_competition.Match.team1_id == team2_id),
                        (models_sport_competition.Match.team2_id == team1_id),
                    ),
                )
                .options(
                    selectinload(models_sport_competition.Match.team1),
                    selectinload(models_sport_competition.Match.team2),
                ),
            )
        )
        .scalars()
        .first()
    )
    return match_model_to_schema(match) if match else None
