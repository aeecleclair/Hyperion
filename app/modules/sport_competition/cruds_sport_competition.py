import logging
from uuid import UUID

from sqlalchemy import and_, delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.schools import schemas_schools
from app.core.users import schemas_users
from app.modules.sport_competition import models_sport_competition as models_competition
from app.modules.sport_competition import (
    schemas_sport_competition as schemas_competition,
)
from app.modules.sport_competition.types_sport_competition import (
    CompetitionGroupType,
    MultipleEditions,
)

logger = logging.getLogger("challenger")


async def add_group(
    group: schemas_competition.Group,
    db: AsyncSession,
):
    db.add(models_competition.CompetitionGroup(**group.model_dump()))
    await db.flush()


async def update_group(
    group_id: UUID,
    group: schemas_competition.GroupEdit,
    db: AsyncSession,
):
    await db.execute(
        update(models_competition.CompetitionGroup)
        .where(models_competition.CompetitionGroup.id == group_id)
        .values(**group.model_dump(exclude_unset=True)),
    )
    await db.flush()


async def delete_group_by_id(
    group_id: UUID,
    db: AsyncSession,
):
    await db.execute(
        delete(models_competition.CompetitionGroup).where(
            models_competition.CompetitionGroup.id == group_id,
        ),
    )
    await db.flush()


async def load_group_by_id(
    group_id: UUID,
    edition_id: UUID,
    db: AsyncSession,
) -> schemas_competition.GroupComplete | None:
    group = (
        (
            await db.execute(
                select(models_competition.CompetitionGroup)
                .where(
                    models_competition.CompetitionGroup.id == group_id,
                )
                .options(
                    selectinload(models_competition.CompetitionGroup.members),
                )
                .filter(
                    models_competition.EditionGroupMembership.edition_id == edition_id,
                ),
            )
        )
        .scalars()
        .first()
    )
    return (
        schemas_competition.GroupComplete(
            id=group.id,
            name=group.name,
            members=[
                schemas_users.CoreUser(**member.__dict__) for member in group.members
            ],
        )
        if group
        else None
    )


async def load_group_by_name(
    name: str,
    db: AsyncSession,
) -> schemas_competition.GroupComplete | None:
    group = await db.get(models_competition.CompetitionGroup, name)
    if group is None:
        return None

    return (
        schemas_competition.GroupComplete(
            id=group.id,
            name=group.name,
            members=[],
        )
        if group
        else None
    )


async def load_all_groups(
    edition_id: UUID,
    db: AsyncSession,
) -> list[schemas_competition.Group]:
    groups = await db.execute(select(models_competition.CompetitionGroup))
    return [
        schemas_competition.Group(**group.__dict__) for group in groups.scalars().all()
    ]


async def load_user_membership_with_group_id(
    user_id: str,
    group_id: UUID | CompetitionGroupType,
    edition_id: UUID,
    db: AsyncSession,
) -> schemas_competition.UserGroupMembership | None:
    membership = await db.get(
        models_competition.EditionGroupMembership,
        (user_id, group_id, edition_id),
    )
    return (
        schemas_competition.UserGroupMembership(
            user_id=membership.user_id,
            group_id=membership.group_id,
            edition_id=membership.edition_id,
        )
        if membership
        else None
    )


async def load_active_user_memberships(
    user_id: str,
    edition_id: UUID,
    db: AsyncSession,
) -> list[schemas_competition.UserGroupMembership]:
    memberships = (
        (
            await db.execute(
                select(models_competition.EditionGroupMembership).where(
                    models_competition.EditionGroupMembership.user_id == user_id,
                    models_competition.EditionGroupMembership.edition_id == edition_id,
                ),
            )
        )
        .scalars()
        .all()
    )
    return [
        schemas_competition.UserGroupMembership(
            user_id=membership.user_id,
            group_id=membership.group_id,
            edition_id=membership.edition_id,
        )
        for membership in memberships
    ]


async def add_user_to_group(
    user_id: str,
    group_id: UUID,
    edition_id: UUID,
    db: AsyncSession,
) -> None:
    db.add(
        models_competition.EditionGroupMembership(
            user_id=user_id,
            group_id=group_id,
            edition_id=edition_id,
        ),
    )
    await db.flush()


async def remove_user_from_group(
    user_id: str,
    group_id: UUID,
    edition_id: UUID,
    db: AsyncSession,
) -> None:
    await db.delete(
        models_competition.EditionGroupMembership(
            user_id=user_id,
            group_id=group_id,
            edition_id=edition_id,
        ),
    )
    await db.flush()


async def load_user_by_id(
    user_id: str,
    edition_id: UUID,
    db: AsyncSession,
) -> schemas_competition.CompetitionUser | None:
    user = (
        (
            await db.execute(
                select(models_competition.CompetitionUser)
                .where(
                    models_competition.CompetitionUser.user_id == user_id,
                )
                .options(
                    selectinload(models_competition.CompetitionUser.competition_groups),
                )
                .filter(
                    models_competition.EditionGroupMembership.edition_id == edition_id,
                ),
            )
        )
        .scalars()
        .first()
    )
    return (
        schemas_competition.CompetitionUser(
            **user.__dict__,
            competition_groups=[
                schemas_competition.Group(
                    id=group.id,
                    name=group.name,
                )
                for group in user.competition_groups
            ],
        )
        if user
        else None
    )


async def add_school(
    school: schemas_competition.SchoolExtension,
    db: AsyncSession,
):
    db.add(models_competition.SchoolExtension(**school.model_dump()))
    await db.flush()


async def update_school(
    school_id: UUID,
    school: schemas_competition.SchoolExtensionEdit,
    db: AsyncSession,
):
    await db.execute(
        update(models_competition.SchoolExtension)
        .where(models_competition.SchoolExtension.school_id == school_id)
        .values(**school.model_dump(exclude_unset=True)),
    )
    await db.flush()


async def delete_school_by_id(
    school_id: UUID,
    db: AsyncSession,
):
    await db.execute(
        delete(models_competition.SchoolExtension).where(
            models_competition.SchoolExtension.school_id == school_id,
        ),
    )
    await db.flush()


async def load_school_by_id(
    school_id: UUID,
    edition_id: UUID,
    db: AsyncSession,
) -> schemas_competition.SchoolExtension | None:
    school_extension = (
        (
            await db.execute(
                select(models_competition.SchoolExtension)
                .where(
                    models_competition.SchoolExtension.school_id == school_id,
                )
                .options(
                    selectinload(models_competition.SchoolExtension.school),
                    selectinload(models_competition.SchoolExtension.general_quota),
                )
                .filter(
                    models_competition.SchoolGeneralQuota.edition_id == edition_id,
                ),
            )
        )
        .scalars()
        .first()
    )
    if school_extension is None:
        return None
    school_dict = school_extension.__dict__
    school = schemas_schools.CoreSchool(**school_dict["school"].__dict__)
    general_quota = schemas_competition.SchoolGeneralQuota(
        **school_dict["general_quota"].__dict__,
    )
    return schemas_competition.SchoolExtension(
        school_id=school_id,
        from_lyon=school_dict["from_lyon"],
        activated=school_dict["activated"],
        school=school,
        general_quota=general_quota,
    )


async def load_school_by_name(
    name: str,
    edition_id: UUID,
    db: AsyncSession,
) -> schemas_competition.SchoolExtension | None:
    school_extension = (
        (
            await db.execute(
                select(models_competition.SchoolExtension)
                .where(
                    models_competition.SchoolExtension.school_id == name,
                )
                .options(
                    selectinload(models_competition.SchoolExtension.school),
                    selectinload(models_competition.SchoolExtension.general_quota),
                )
                .filter(
                    models_competition.SchoolGeneralQuota.edition_id == edition_id,
                ),
            )
        )
        .scalars()
        .first()
    )
    return (
        schemas_competition.SchoolExtension(
            school_id=school_extension.school_id,
            from_lyon=school_extension.from_lyon,
            activated=school_extension.activated,
            school=schemas_schools.CoreSchool(**school_extension.school.__dict__),
            general_quota=schemas_competition.SchoolGeneralQuota(
                **school_extension.general_quota.__dict__,
            ),
        )
        if school_extension
        else None
    )


async def load_all_schools(
    edition_id: UUID,
    db: AsyncSession,
) -> list[schemas_competition.SchoolExtension]:
    school_extensions = await db.execute(
        select(models_competition.SchoolExtension)
        .options(
            selectinload(models_competition.SchoolExtension.school),
            selectinload(models_competition.SchoolExtension.general_quota),
        )
        .filter(
            models_competition.SchoolGeneralQuota.edition_id == edition_id,
        ),
    )

    return [
        schemas_competition.SchoolExtension(
            school_id=school_extension.school_id,
            from_lyon=school_extension.from_lyon,
            activated=school_extension.activated,
            school=schemas_schools.CoreSchool(**school_extension.school.__dict__),
            general_quota=schemas_competition.SchoolGeneralQuota(
                **school_extension.general_quota.__dict__,
            ),
        )
        for school_extension in school_extensions.scalars().all()
    ]


async def store_participant(
    participant: schemas_competition.Participant,
    db: AsyncSession,
):
    stored_participant = await load_participant_by_ids(
        participant.user_id,
        participant.sport_id,
        participant.edition_id,
        db,
    )
    if stored_participant is None:
        db.add(
            models_competition.Participant(
                user_id=participant.user_id,
                sport_id=participant.sport_id,
                edition_id=participant.edition_id,
                team_id=participant.team_id,
                school_id=participant.school_id,
                substitute=participant.substitute,
                license=participant.license,
                validated=participant.validated,
            ),
        )
    else:
        await db.execute(
            update(models_competition.Participant)
            .where(
                models_competition.Participant.user_id == participant.user_id,
                models_competition.Participant.sport_id == participant.sport_id,
            )
            .values(**participant.model_dump()),
        )
    await db.flush()


async def delete_participant_by_ids(
    user_id: str,
    sport_id: UUID,
    edition_id: UUID,
    db: AsyncSession,
):
    await db.execute(
        delete(models_competition.Participant).where(
            models_competition.Participant.user_id == user_id,
            models_competition.Participant.sport_id == sport_id,
            models_competition.Participant.edition_id == edition_id,
        ),
    )
    await db.flush()


async def load_participant_by_ids(
    user_id: str,
    sport_id: UUID,
    edition_id: UUID,
    db: AsyncSession,
) -> schemas_competition.ParticipantComplete | None:
    participant = (
        (
            await db.execute(
                select(models_competition.Participant)
                .where(
                    models_competition.Participant.user_id == user_id,
                    models_competition.Participant.sport_id == sport_id,
                    models_competition.Participant.edition_id == edition_id,
                )
                .options(
                    selectinload(models_competition.Participant.user),
                ),
            )
        )
        .scalars()
        .first()
    )
    return (
        schemas_competition.ParticipantComplete(
            user_id=participant.user_id,
            sport_id=participant.sport_id,
            edition_id=participant.edition_id,
            team_id=participant.team_id,
            school_id=participant.school_id,
            substitute=participant.substitute,
            license=participant.license,
            validated=participant.validated,
            user=schemas_users.CoreUser(**participant.user.__dict__),
        )
        if participant
        else None
    )


async def load_all_participants(
    edition_id: UUID,
    db: AsyncSession,
) -> list[schemas_competition.ParticipantComplete]:
    participants = await db.execute(
        select(models_competition.Participant)
        .where(
            models_competition.Participant.edition_id == edition_id,
        )
        .options(
            selectinload(models_competition.Participant.user),
        ),
    )
    return [
        schemas_competition.ParticipantComplete(
            user_id=participant.user_id,
            sport_id=participant.sport_id,
            edition_id=participant.edition_id,
            team_id=participant.team_id,
            school_id=participant.school_id,
            substitute=participant.substitute,
            license=participant.license,
            validated=participant.validated,
            user=schemas_users.CoreUser(**participant.user.__dict__),
        )
        for participant in participants.scalars().all()
    ]


async def load_participants_by_school_id(
    school_id: UUID,
    edition_id: UUID,
    db: AsyncSession,
) -> list[schemas_competition.ParticipantComplete]:
    participants = (
        (
            await db.execute(
                select(models_competition.Participant)
                .where(
                    models_competition.Participant.edition_id == edition_id,
                    models_competition.Participant.school_id == school_id,
                )
                .options(
                    selectinload(models_competition.Participant.user),
                ),
            )
        )
        .scalars()
        .all()
    )
    return [
        schemas_competition.ParticipantComplete(
            user_id=participant.user_id,
            sport_id=participant.sport_id,
            edition_id=participant.edition_id,
            team_id=participant.team_id,
            school_id=participant.school_id,
            substitute=participant.substitute,
            license=participant.license,
            validated=participant.validated,
            user=schemas_users.CoreUser(**participant.user.__dict__),
        )
        for participant in participants
    ]


async def load_participants_by_sport_id(
    sport_id: UUID,
    edition_id: UUID,
    db: AsyncSession,
) -> list[schemas_competition.ParticipantComplete]:
    participants = (
        (
            await db.execute(
                select(models_competition.Participant)
                .where(
                    models_competition.Participant.sport_id == sport_id,
                    models_competition.Participant.edition_id == edition_id,
                )
                .options(
                    selectinload(models_competition.Participant.user),
                ),
            )
        )
        .scalars()
        .all()
    )
    return [
        schemas_competition.ParticipantComplete(
            user_id=participant.user_id,
            sport_id=participant.sport_id,
            edition_id=participant.edition_id,
            team_id=participant.team_id,
            school_id=participant.school_id,
            substitute=participant.substitute,
            license=participant.license,
            validated=participant.validated,
            user=schemas_users.CoreUser(**participant.user.__dict__),
        )
        for participant in participants
    ]


async def load_participants_by_school_and_sport_ids(
    school_id: UUID,
    sport_id: UUID,
    edition_id: UUID,
    db: AsyncSession,
) -> list[schemas_competition.ParticipantComplete]:
    participants = (
        (
            await db.execute(
                select(models_competition.Participant)
                .where(
                    models_competition.Participant.sport_id == sport_id,
                    models_competition.Participant.edition_id == edition_id,
                    models_competition.Participant.school_id == school_id,
                )
                .options(
                    selectinload(models_competition.Participant.user),
                ),
            )
        )
        .scalars()
        .all()
    )
    return [
        schemas_competition.ParticipantComplete(
            user_id=participant.user_id,
            sport_id=participant.sport_id,
            edition_id=participant.edition_id,
            team_id=participant.team_id,
            school_id=participant.school_id,
            substitute=participant.substitute,
            license=participant.license,
            validated=participant.validated,
            user=schemas_users.CoreUser(**participant.user.__dict__),
        )
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
            models_competition.Participant.sport_id == sport_id,
            models_competition.Participant.edition_id == edition_id,
            models_competition.Participant.school_id == school_id,
            models_competition.Participant.validated,
        ),
    )
    return result.scalar() or 0


async def store_quota(
    quota: schemas_competition.Quota,
    db: AsyncSession,
):
    stored_quota = await load_sport_quota_by_ids(
        quota.school_id,
        quota.sport_id,
        quota.edition_id,
        db,
    )
    if stored_quota is None:
        db.add(models_competition.SchoolSportQuota(**quota.model_dump()))
    else:
        await db.execute(
            update(models_competition.SchoolSportQuota)
            .where(
                models_competition.SchoolSportQuota.school_id == quota.school_id,
                models_competition.SchoolSportQuota.sport_id == quota.sport_id,
            )
            .values(**quota.model_dump()),
        )
    await db.flush()


async def delete_quota_by_ids(
    school_id: UUID,
    sport_id: UUID,
    edition_id: UUID,
    db: AsyncSession,
):
    await db.execute(
        delete(models_competition.SchoolSportQuota).where(
            models_competition.SchoolSportQuota.school_id == school_id,
            models_competition.SchoolSportQuota.sport_id == sport_id,
            models_competition.SchoolSportQuota.edition_id == edition_id,
        ),
    )
    await db.flush()


async def load_sport_quota_by_ids(
    school_id: UUID,
    sport_id: UUID,
    edition_id: UUID,
    db: AsyncSession,
) -> schemas_competition.Quota | None:
    quota = await db.get(
        models_competition.SchoolSportQuota,
        (school_id, sport_id, edition_id),
    )
    return schemas_competition.Quota(**quota.__dict__) if quota else None


async def load_all_quotas_by_school_id(
    school_id: UUID,
    edition_id: UUID,
    db: AsyncSession,
) -> list[schemas_competition.Quota]:
    quotas = await db.execute(
        select(models_competition.SchoolSportQuota).where(
            models_competition.SchoolSportQuota.school_id == school_id,
            models_competition.SchoolSportQuota.edition_id == edition_id,
        ),
    )
    return [
        schemas_competition.Quota(**quota.__dict__) for quota in quotas.scalars().all()
    ]


async def load_all_quotas_by_sport_id(
    sport_id: UUID,
    edition_id: UUID,
    db: AsyncSession,
) -> list[schemas_competition.Quota]:
    quotas = await db.execute(
        select(models_competition.SchoolSportQuota).where(
            models_competition.SchoolSportQuota.sport_id == sport_id,
            models_competition.SchoolSportQuota.edition_id == edition_id,
        ),
    )
    return [
        schemas_competition.Quota(**quota.__dict__) for quota in quotas.scalars().all()
    ]


async def store_sport(
    sport: schemas_competition.Sport,
    db: AsyncSession,
):
    stored_sport = await load_sport_by_id(sport.id, db)
    if stored_sport is None:
        db.add(models_competition.Sport(**sport.model_dump()))
    else:
        await db.execute(
            update(models_competition.Sport)
            .where(models_competition.Sport.id == sport.id)
            .values(**sport.model_dump()),
        )
    await db.flush()


async def delete_sport_by_id(
    sport_id: UUID,
    db: AsyncSession,
):
    await db.execute(
        delete(models_competition.Sport).where(models_competition.Sport.id == sport_id),
    )
    await db.flush()


async def load_sport_by_id(
    sport_id: UUID,
    db: AsyncSession,
) -> schemas_competition.Sport | None:
    sport = await db.get(models_competition.Sport, sport_id)
    return schemas_competition.Sport(**sport.__dict__) if sport else None


async def load_sport_by_name(
    name: str,
    db: AsyncSession,
) -> schemas_competition.Sport | None:
    sport = await db.get(models_competition.Sport, name)
    return schemas_competition.Sport(**sport.__dict__) if sport else None


async def load_all_sports(
    db: AsyncSession,
) -> list[schemas_competition.Sport]:
    sports = await db.execute(select(models_competition.Sport))
    return [
        schemas_competition.Sport(**sport.__dict__) for sport in sports.scalars().all()
    ]


async def store_team(
    team: schemas_competition.Team,
    db: AsyncSession,
):
    stored_team = await load_team_by_id(team.id, db)
    if stored_team is None:
        db.add(models_competition.Team(**team.model_dump()))
    else:
        await db.execute(
            update(models_competition.Team)
            .where(models_competition.Team.id == team.id)
            .values(**team.model_dump()),
        )
    await db.flush()


async def delete_team_by_id(
    team_id: UUID,
    db: AsyncSession,
):
    await db.execute(
        delete(models_competition.Team).where(models_competition.Team.id == team_id),
    )
    await db.flush()


async def load_team_by_id(
    team_id,
    db: AsyncSession,
) -> schemas_competition.TeamComplete | None:
    team = (
        (
            await db.execute(
                select(models_competition.Team)
                .where(models_competition.Team.id == team_id)
                .options(
                    selectinload(models_competition.Team.participants),
                ),
            )
        )
        .scalars()
        .first()
    )
    return (
        schemas_competition.TeamComplete(
            name=team.name,
            school_id=team.school_id,
            sport_id=team.sport_id,
            edition_id=team.edition_id,
            captain_id=team.captain_id,
            id=team.id,
            participants=[
                schemas_competition.Participant(**user.__dict__)
                for user in team.participants
            ],
        )
        if team
        else None
    )


async def load_team_by_name(
    name: str,
    edition_id: UUID,
    db: AsyncSession,
) -> schemas_competition.TeamComplete | None:
    team = (
        (
            await db.execute(
                select(models_competition.Team).where(
                    models_competition.Team.name == name,
                    models_competition.Team.edition_id == edition_id,
                ),
            )
        )
        .scalars()
        .first()
    )
    return (
        schemas_competition.TeamComplete(
            name=team.name,
            school_id=team.school_id,
            sport_id=team.sport_id,
            edition_id=team.edition_id,
            captain_id=team.captain_id,
            id=team.id,
            participants=[],
        )
        if team
        else None
    )


def team_model_to_schemas(
    team: models_competition.Team,
) -> schemas_competition.TeamComplete:
    participants = []
    for participant in team.participants:
        participant_dict = participant.__dict__
        participant_dict.pop("user")
        user = schemas_users.CoreUser(**participant.user.__dict__)
        participants.append(
            schemas_competition.ParticipantComplete(
                **participant_dict,
                user=user,
            ),
        )
    return schemas_competition.TeamComplete(
        name=team.name,
        school_id=team.school_id,
        sport_id=team.sport_id,
        edition_id=team.edition_id,
        captain_id=team.captain_id,
        id=team.id,
        participants=participants,
    )


async def load_all_teams_by_sport_id(
    sport_id: UUID,
    edition_id: UUID,
    db: AsyncSession,
) -> list[schemas_competition.TeamComplete]:
    db_teams = await db.execute(
        select(models_competition.Team)
        .where(
            models_competition.Team.sport_id == sport_id,
            models_competition.Team.edition_id == edition_id,
        )
        .options(
            selectinload(models_competition.Team.participants),
        ),
    )
    return [team_model_to_schemas(team) for team in db_teams.scalars().all()]


async def load_all_teams_by_school_id(
    school_id: UUID,
    edition_id: UUID,
    db: AsyncSession,
) -> list[schemas_competition.TeamComplete]:
    teams = await db.execute(
        select(models_competition.Team)
        .where(
            models_competition.Team.school_id == school_id,
            models_competition.Team.edition_id == edition_id,
        )
        .options(
            selectinload(models_competition.Team.participants),
        ),
    )
    return [team_model_to_schemas(team) for team in teams.scalars().all()]


async def load_all_teams_by_school_and_sport_ids(
    school_id: UUID,
    team_id: UUID,
    edition_id: UUID,
    db: AsyncSession,
) -> list[schemas_competition.TeamComplete]:
    teams = await db.execute(
        select(models_competition.Team)
        .where(
            models_competition.Team.school_id == school_id,
            models_competition.Team.sport_id == team_id,
            models_competition.Team.edition_id == edition_id,
        )
        .options(
            selectinload(models_competition.Team.participants),
        ),
    )
    return [team_model_to_schemas(team) for team in teams.scalars().all()]


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
            models_competition.Team.school_id == school_id,
            models_competition.Team.sport_id == sport_id,
            models_competition.Team.edition_id == edition_id,
        )
        .with_for_update(),
    )
    return result.scalar() or 0


async def store_edition(
    edition: schemas_competition.CompetitionEdition,
    db: AsyncSession,
):
    db.add(models_competition.CompetitionEdition(**edition.model_dump()))
    await db.flush()


async def update_edition(
    edition_id: UUID,
    edition: schemas_competition.CompetitionEditionEdit,
    db: AsyncSession,
):
    await db.execute(
        update(models_competition.CompetitionEdition)
        .where(models_competition.CompetitionEdition.id == edition_id)
        .values(**edition.model_dump()),
    )
    await db.flush()


async def delete_edition_by_id(
    edition_id: UUID,
    db: AsyncSession,
):
    await db.execute(
        delete(models_competition.CompetitionEdition).where(
            models_competition.CompetitionEdition.id == edition_id,
        ),
    )
    await db.flush()


async def load_edition_by_id(
    edition_id,
    db: AsyncSession,
) -> schemas_competition.CompetitionEdition | None:
    edition = await db.get(models_competition.CompetitionEdition, edition_id)
    return (
        schemas_competition.CompetitionEdition(**edition.__dict__) if edition else None
    )


async def load_edition_by_name(
    name: str,
    db: AsyncSession,
) -> schemas_competition.CompetitionEdition | None:
    edition = await db.get(models_competition.CompetitionEdition, name)
    return (
        schemas_competition.CompetitionEdition(**edition.__dict__) if edition else None
    )


async def load_active_edition(
    db: AsyncSession,
) -> schemas_competition.CompetitionEdition | None:
    edition = (
        (
            await db.execute(
                select(models_competition.CompetitionEdition).where(
                    models_competition.CompetitionEdition.activated,
                ),
            )
        )
        .scalars()
        .first()
    )
    return (
        schemas_competition.CompetitionEdition(**edition.__dict__) if edition else None
    )


async def load_all_editions(
    db: AsyncSession,
) -> list[schemas_competition.CompetitionEdition]:
    editions = await db.execute(select(models_competition.CompetitionEdition))
    return [
        schemas_competition.CompetitionEdition(**edition.__dict__)
        for edition in editions.scalars().all()
    ]


async def store_match(
    match: schemas_competition.Match,
    db: AsyncSession,
):
    stored_match = await load_match_by_id(match.id, db)
    if stored_match is None:
        db.add(models_competition.Match(**match.model_dump()))
    else:
        await db.execute(
            update(models_competition.Match)
            .where(models_competition.Match.id == match.id)
            .values(**match.model_dump()),
        )
    await db.flush()


async def delete_match_by_id(
    match_id: UUID,
    db: AsyncSession,
):
    await db.execute(
        delete(models_competition.Match).where(models_competition.Match.id == match_id),
    )
    await db.flush()


async def load_match_by_id(
    match_id,
    db: AsyncSession,
) -> schemas_competition.Match | None:
    match = await db.get(models_competition.Match, match_id)
    return schemas_competition.Match(**match.__dict__) if match else None


async def load_all_matches_by_sport_id(
    sport_id: UUID,
    edition_id: UUID,
    db: AsyncSession,
) -> list[schemas_competition.Match]:
    matches = await db.execute(
        select(models_competition.Match)
        .where(
            models_competition.Match.sport_id == sport_id,
            models_competition.Match.edition_id == edition_id,
        )
        .options(
            selectinload(models_competition.Match.team1),
            selectinload(models_competition.Match.team2),
        ),
    )

    return [
        schemas_competition.Match(
            id=match.id,
            name=match.name,
            edition_id=match.edition_id,
            sport_id=match.sport_id,
            team1_id=match.team1_id,
            team2_id=match.team2_id,
            datetime=match.date,
            score_team1=match.score_team1,
            score_team2=match.score_team2,
            location=match.location,
            winner_id=match.winner_id,
            team1=schemas_competition.Team(**match.team1.__dict__),
            team2=schemas_competition.Team(**match.team2.__dict__),
        )
        for match in matches.scalars().all()
    ]


async def load_all_matches_by_school_id(
    school_id: UUID,
    edition_id: UUID,
    db: AsyncSession,
) -> list[schemas_competition.Match]:
    matches = await db.execute(
        select(models_competition.Match)
        .where(
            models_competition.Match.edition_id == edition_id,
            (
                models_competition.Match.team1_id.in_(
                    select(models_competition.Team.id).where(
                        models_competition.Team.school_id == school_id,
                    ),
                )
                | models_competition.Match.team2_id.in_(
                    select(models_competition.Team.id).where(
                        models_competition.Team.school_id == school_id,
                    ),
                )
            ),
        )
        .options(
            selectinload(models_competition.Match.team1),
            selectinload(models_competition.Match.team2),
        ),
    )

    return [
        schemas_competition.Match(
            id=match.id,
            name=match.name,
            edition_id=match.edition_id,
            sport_id=match.sport_id,
            team1_id=match.team1_id,
            team2_id=match.team2_id,
            date=match.date,
            score_team1=match.score_team1,
            score_team2=match.score_team2,
            location=match.location,
            winner_id=match.winner_id,
            team1=schemas_competition.Team(**match.team1.__dict__),
            team2=schemas_competition.Team(**match.team2.__dict__),
        )
        for match in matches.scalars().all()
    ]


async def load_match_by_teams_ids(
    team1_id: UUID,
    team2_id: UUID,
    db: AsyncSession,
) -> schemas_competition.Match | None:
    match = (
        (
            await db.execute(
                select(models_competition.Match)
                .where(
                    and_(
                        models_competition.Match.team1_id == team1_id,
                        models_competition.Match.team2_id == team2_id,
                    )
                    | and_(
                        (models_competition.Match.team1_id == team2_id),
                        (models_competition.Match.team2_id == team1_id),
                    ),
                )
                .options(
                    selectinload(models_competition.Match.team1),
                    selectinload(models_competition.Match.team2),
                ),
            )
        )
        .scalars()
        .first()
    )
    return (
        schemas_competition.Match(
            id=match.id,
            name=match.name,
            edition_id=match.edition_id,
            sport_id=match.sport_id,
            team1_id=match.team1_id,
            team2_id=match.team2_id,
            date=match.date,
            score_team1=match.score_team1,
            score_team2=match.score_team2,
            location=match.location,
            winner_id=match.winner_id,
            team1=schemas_competition.Team(**match.team1.__dict__),
            team2=schemas_competition.Team(**match.team2.__dict__),
        )
        if match
        else None
    )
