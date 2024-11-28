import logging

from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import models_core, schemas_core
from app.modules.sport_competition import models_sport_competition as models_competition
from app.modules.sport_competition import (
    schemas_sport_competition as schemas_competition,
)
from app.modules.sport_competition.types_sport_competition import (
    MultipleEditions,
)

logger = logging.getLogger("challenger")


async def store_group(
    group: schemas_competition.Group,
    db: AsyncSession,
):
    stored_group = await load_group_by_id(group.id, db)
    if stored_group is None:
        db.add(models_competition.CompetitionGroup(**group.model_dump()))
    else:
        await db.execute(
            update(models_competition.CompetitionGroup)
            .where(models_competition.CompetitionGroup.id == group.id)
            .values(**group.model_dump()),
        )
    try:
        await db.commit()
    except IntegrityError as error:
        logger.exception("Could not store group")
        await db.rollback()
        raise error from None


async def delete_group_by_id(
    group_id: str,
    db: AsyncSession,
):
    await db.execute(
        delete(models_competition.CompetitionGroup).where(
            models_competition.CompetitionGroup.id == group_id,
        ),
    )
    await db.commit()


async def load_group_by_id(
    group_id: str,
    db: AsyncSession,
) -> schemas_competition.GroupComplete | None:
    group = await db.get(models_competition.CompetitionGroup, group_id)
    if group is None:
        return None
    memberships = (
        (
            await db.execute(
                select(models_competition.AnnualGroupMembership).where(
                    models_competition.AnnualGroupMembership.group_id == group_id,
                ),
            )
        )
        .scalars()
        .all()
    )
    members = (
        (
            await db.execute(
                select(models_core.CoreUser).where(
                    models_core.CoreUser.id.in_(
                        [membership.user_id for membership in memberships],
                    ),
                ),
            )
        )
        .scalars()
        .all()
    )
    return schemas_competition.GroupComplete(**group.__dict__, members=members)


async def load_group_by_name(
    name: str,
    db: AsyncSession,
) -> schemas_competition.GroupComplete | None:
    group = await db.get(models_competition.CompetitionGroup, name)
    if group is None:
        return None

    memberships = (
        (
            await db.execute(
                select(models_competition.AnnualGroupMembership).where(
                    models_competition.AnnualGroupMembership.group_id == group.id,
                ),
            )
        )
        .scalars()
        .all()
    )

    members = (
        (
            await db.execute(
                select(models_core.CoreUser).where(
                    models_core.CoreUser.id.in_(
                        [membership.user_id for membership in memberships],
                    ),
                ),
            )
        )
        .scalars()
        .all()
    )
    return (
        schemas_competition.GroupComplete(**group.__dict__, members=members)
        if group
        else None
    )


async def load_all_groups(
    db: AsyncSession,
) -> list[schemas_competition.Group]:
    groups = await db.execute(select(models_competition.CompetitionGroup))
    return [
        schemas_competition.Group(**group.__dict__) for group in groups.scalars().all()
    ]


async def add_user_to_group(
    user_id: str,
    group_id: str,
    edition_id: str,
    db: AsyncSession,
) -> None:
    db.add(
        models_competition.AnnualGroupMembership(
            user_id=user_id,
            group_id=group_id,
            edition_id=edition_id,
        ),
    )
    try:
        await db.commit()
    except IntegrityError as error:
        await db.rollback()
        raise error from None


async def remove_user_from_group(
    user_id: str,
    group_id: str,
    edition_id: str,
    db: AsyncSession,
) -> None:
    await db.delete(
        models_competition.AnnualGroupMembership(
            user_id=user_id,
            group_id=group_id,
            edition_id=edition_id,
        ),
    )
    try:
        await db.commit()
    except IntegrityError as error:
        await db.rollback()
        raise error from None


async def store_school(
    school: schemas_competition.SchoolExtension,
    db: AsyncSession,
):
    stored_school = await load_school_by_id(school.id, db)
    if stored_school is None:
        db.add(models_competition.SchoolExtension(**school.model_dump()))
    else:
        await db.execute(
            update(models_competition.SchoolExtension)
            .where(models_competition.SchoolExtension.id == school.id)
            .values(**school.model_dump()),
        )
    try:
        await db.commit()
    except IntegrityError as error:
        await db.rollback()
        raise error from None


async def delete_school_by_id(
    school_id: str,
    db: AsyncSession,
):
    await db.execute(
        delete(models_competition.SchoolExtension).where(
            models_competition.SchoolExtension.id == school_id,
        ),
    )
    await db.commit()


async def load_school_by_id(
    school_id: str,
    db: AsyncSession,
) -> schemas_competition.SchoolExtension | None:
    school_extension = await db.get(models_competition.SchoolExtension, school_id)
    school = (
        schemas_core.CoreSchool(**school_extension.school.__dict__)
        if school_extension
        else None
    )
    general_quota = (
        schemas_competition.SchoolGeneralQuota(
            **school_extension.general_quota.__dict__,
        )
        if school_extension
        else None
    )
    return (
        schemas_competition.SchoolExtension(
            id=school_id,
            from_lyon=school_extension.from_lyon,
            activated=school_extension.activated,
            school=school,
            general_quota=general_quota,
        )
        if school_extension
        else None
    )


async def load_school_by_name(
    name: str,
    db: AsyncSession,
) -> schemas_competition.SchoolExtension | None:
    school_extension = await db.get(models_competition.SchoolExtension, name)
    school = (
        schemas_core.CoreSchool(**school_extension.school.__dict__)
        if school_extension
        else None
    )
    general_quota = (
        schemas_competition.SchoolGeneralQuota(
            **school_extension.general_quota.__dict__,
        )
        if school_extension
        else None
    )
    return (
        schemas_competition.SchoolExtension(
            id=name,
            from_lyon=school_extension.from_lyon,
            activated=school_extension.activated,
            school=school,
            general_quota=general_quota,
        )
        if school_extension
        else None
    )


async def load_all_schools(
    db: AsyncSession,
) -> list[schemas_competition.SchoolExtension]:
    school_extensions = await db.execute(select(models_competition.SchoolExtension))
    return [
        schemas_competition.SchoolExtension(
            id=school_extension.id,
            from_lyon=school_extension.from_lyon,
            activated=school_extension.activated,
            school=schemas_core.CoreSchool(**school_extension.school.__dict__),
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
        db.add(models_competition.Participant(**participant.model_dump()))
    else:
        await db.execute(
            update(models_competition.Participant)
            .where(
                models_competition.Participant.user_id == participant.user_id,
                models_competition.Participant.sport_id == participant.sport_id,
            )
            .values(**participant.model_dump()),
        )
    try:
        await db.commit()
    except IntegrityError as error:
        await db.rollback()
        raise error from None


async def delete_participant_by_ids(
    user_id: str,
    sport_id: str,
    edition_id: str,
    db: AsyncSession,
):
    await db.execute(
        delete(models_competition.Participant).where(
            models_competition.Participant.user_id == user_id,
            models_competition.Participant.sport_id == sport_id,
            models_competition.Participant.edition_id == edition_id,
        ),
    )
    await db.commit()


async def load_participant_by_ids(
    user_id: str,
    sport_id: str,
    edition_id: str,
    db: AsyncSession,
) -> schemas_competition.ParticipantComplete | None:
    participant = (
        await db.execute(
            select(models_competition.Participant).where(
                models_competition.Participant.user_id == user_id,
                models_competition.Participant.sport_id == sport_id,
                models_competition.Participant.edition_id == edition_id,
            ),
        )
    ).scalar()
    return (
        schemas_competition.ParticipantComplete(**participant.__dict__)
        if participant
        else None
    )


async def load_all_participants(
    edition_id: str,
    db: AsyncSession,
) -> list[schemas_competition.ParticipantComplete]:
    participants = await db.execute(
        select(models_competition.Participant).where(
            models_competition.Participant.edition_id == edition_id,
        ),
    )
    return [
        schemas_competition.ParticipantComplete(**participant.__dict__)
        for participant in participants.scalars().all()
    ]


async def load_participants_by_school_id(
    school_id: str,
    edition_id: str,
    db: AsyncSession,
) -> list[schemas_competition.ParticipantComplete]:
    participants = (
        (
            await db.execute(
                select(models_competition.Participant).where(
                    models_competition.Participant.edition_id == edition_id,
                    models_competition.Participant.user_id.in_(
                        select(models_core.CoreUser.id).where(
                            models_core.CoreUser.school_id == school_id,
                        ),
                    ),
                ),
            )
        )
        .scalars()
        .all()
    )
    return [
        schemas_competition.ParticipantComplete(**participant.__dict__)
        for participant in participants
    ]


async def load_participants_by_sport_id(
    sport_id: str,
    edition_id: str,
    db: AsyncSession,
) -> list[schemas_competition.ParticipantComplete]:
    participants = (
        (
            await db.execute(
                select(models_competition.Participant).where(
                    models_competition.Participant.sport_id == sport_id,
                    models_competition.Participant.edition_id == edition_id,
                ),
            )
        )
        .scalars()
        .all()
    )
    return [
        schemas_competition.ParticipantComplete(**participant.__dict__)
        for participant in participants
    ]


async def load_participants_by_school_and_sport_ids(
    school_id: str,
    sport_id: str,
    edition_id: str,
    db: AsyncSession,
) -> list[schemas_competition.ParticipantComplete]:
    participants = (
        (
            await db.execute(
                select(models_competition.Participant).where(
                    models_competition.Participant.sport_id == sport_id,
                    models_competition.Participant.edition_id == edition_id,
                    models_competition.Participant.user_id.in_(
                        select(models_core.CoreUser.id).where(
                            models_core.CoreUser.school_id == school_id,
                        ),
                    ),
                ),
            )
        )
        .scalars()
        .all()
    )
    return [
        schemas_competition.ParticipantComplete(**participant.__dict__)
        for participant in participants
    ]


async def store_quota(
    quota: schemas_competition.Quota,
    db: AsyncSession,
):
    stored_quota = await load_quota_by_ids(
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
    try:
        await db.commit()
    except IntegrityError as error:
        await db.rollback()
        raise error from None


async def delete_quota_by_ids(
    school_id: str,
    sport_id: str,
    edition_id: str,
    db: AsyncSession,
):
    await db.execute(
        delete(models_competition.SchoolSportQuota).where(
            models_competition.SchoolSportQuota.school_id == school_id,
            models_competition.SchoolSportQuota.sport_id == sport_id,
            models_competition.SchoolSportQuota.edition_id == edition_id,
        ),
    )
    await db.commit()


async def load_quota_by_ids(
    school_id: str,
    sport_id: str,
    edition_id: str,
    db: AsyncSession,
) -> schemas_competition.QuotaComplete | None:
    quota = (
        await db.execute(
            select(models_competition.SchoolSportQuota).where(
                models_competition.SchoolSportQuota.school_id == school_id,
                models_competition.SchoolSportQuota.sport_id == sport_id,
                models_competition.SchoolSportQuota.edition_id == edition_id,
            ),
        )
    ).scalar()
    return schemas_competition.QuotaComplete(**quota.__dict__) if quota else None


async def load_all_quotas_by_school_id(
    school_id: str,
    edition_id: str,
    db: AsyncSession,
) -> list[schemas_competition.QuotaComplete]:
    quotas = await db.execute(
        select(models_competition.SchoolSportQuota).where(
            models_competition.SchoolSportQuota.school_id == school_id,
            models_competition.SchoolSportQuota.edition_id == edition_id,
        ),
    )
    return [
        schemas_competition.QuotaComplete(**quota.__dict__)
        for quota in quotas.scalars().all()
    ]


async def load_all_quotas_by_sport_id(
    sport_id: str,
    edition_id: str,
    db: AsyncSession,
) -> list[schemas_competition.QuotaComplete]:
    quotas = await db.execute(
        select(models_competition.SchoolSportQuota).where(
            models_competition.SchoolSportQuota.sport_id == sport_id,
            models_competition.SchoolSportQuota.edition_id == edition_id,
        ),
    )
    return [
        schemas_competition.QuotaComplete(**quota.__dict__)
        for quota in quotas.scalars().all()
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
    try:
        await db.commit()
    except IntegrityError as error:
        await db.rollback()
        raise error from None


async def delete_sport_by_id(
    sport_id: str,
    db: AsyncSession,
):
    await db.execute(
        delete(models_competition.Sport).where(models_competition.Sport.id == sport_id),
    )
    await db.commit()


async def load_sport_by_id(
    sport_id,
    db: AsyncSession,
) -> schemas_competition.Sport | None:
    sport = await db.get(models_competition.Sport, sport_id)
    return schemas_competition.Sport(**sport.__dict__) if sport else None


async def load_sport_by_name(
    name,
    db: AsyncSession,
) -> schemas_competition.Sport | None:
    sport = await db.get(models_competition.Sport, name)
    return schemas_competition.Sport(**sport.__dict__) if sport else None


async def load_all_sports(
    self,
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
    try:
        await db.commit()
    except IntegrityError as error:
        await db.rollback()
        raise error from None


async def delete_team_by_id(
    team_id: str,
    db: AsyncSession,
):
    await db.execute(
        delete(models_competition.Team).where(models_competition.Team.id == team_id),
    )
    await db.commit()


async def load_team_by_id(
    team_id,
    db: AsyncSession,
) -> schemas_competition.TeamComplete | None:
    team = await db.get(models_competition.Team, team_id)
    return schemas_competition.TeamComplete(**team.__dict__) if team else None


async def load_team_by_name(
    name: str,
    edition_id: str,
    db: AsyncSession,
) -> schemas_competition.TeamComplete | None:
    team = await db.execute(
        select(models_competition.Team).where(
            models_competition.Team.name == name,
            models_competition.Team.edition_id == edition_id,
        ),
    )
    return schemas_competition.TeamComplete(**team.__dict__) if team else None


async def load_all_teams_by_sport_id(
    sport_id: str,
    edition_id: str,
    db: AsyncSession,
) -> list[schemas_competition.TeamComplete]:
    teams = await db.execute(
        select(models_competition.Team).where(
            models_competition.Team.sport_id == sport_id,
            models_competition.Team.edition_id == edition_id,
        ),
    )
    return [
        schemas_competition.TeamComplete(**team.__dict__)
        for team in teams.scalars().all()
    ]


async def load_all_teams_by_school_id(
    school_id: str,
    edition_id: str,
    db: AsyncSession,
) -> list[schemas_competition.TeamComplete]:
    teams = await db.execute(
        select(models_competition.Team).where(
            models_competition.Team.school_id == school_id,
            models_competition.Team.edition_id == edition_id,
        ),
    )
    return [
        schemas_competition.TeamComplete(**team.__dict__)
        for team in teams.scalars().all()
    ]


async def load_all_teams_by_school_and_sport_ids(
    school_id: str,
    team_id: str,
    edition_id: str,
    db: AsyncSession,
) -> list[schemas_competition.TeamComplete]:
    teams = await db.execute(
        select(models_competition.Team).where(
            models_competition.Team.school_id == school_id,
            models_competition.Team.sport_id == team_id,
            models_competition.Team.edition_id == edition_id,
        ),
    )
    return [
        schemas_competition.TeamComplete(**team.__dict__)
        for team in teams.scalars().all()
    ]


async def store_edition(
    edition: schemas_competition.CompetitionEdition,
    db: AsyncSession,
):
    stored_edition = await load_edition_by_id(edition.id, db)
    if stored_edition is None:
        db.add(models_competition.CompetitionEdition(**edition.model_dump()))
    else:
        await db.execute(
            update(models_competition.CompetitionEdition)
            .where(models_competition.CompetitionEdition.id == edition.id)
            .values(**edition.model_dump()),
        )
        active = await load_active_edition(db)
        if active and active.id != edition.id and edition.activated:
            raise MultipleEditions

    try:
        await db.commit()
    except IntegrityError as error:
        await db.rollback()
        raise error from None


async def delete_edition_by_id(
    edition_id: str,
    db: AsyncSession,
):
    await db.execute(
        delete(models_competition.CompetitionEdition).where(
            models_competition.CompetitionEdition.id == edition_id,
        ),
    )
    await db.commit()


async def load_edition_by_id(
    edition_id,
    db: AsyncSession,
) -> schemas_competition.CompetitionEdition | None:
    edition = await db.get(models_competition.CompetitionEdition, edition_id)
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
