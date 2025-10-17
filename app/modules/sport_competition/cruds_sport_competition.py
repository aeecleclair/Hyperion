import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import and_, delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.core.schools import models_schools
from app.core.schools.schemas_schools import CoreSchool
from app.core.users import models_users, schemas_users
from app.modules.sport_competition import (
    models_sport_competition,
    schemas_sport_competition,
)
from app.modules.sport_competition.types_sport_competition import (
    CompetitionGroupType,
    ProductPublicType,
    ProductSchoolType,
)
from app.modules.sport_competition.utils.schemas_converters import (
    competition_user_model_to_schema,
    match_model_to_schema,
    participant_complete_model_to_schema,
    purchase_model_to_schema,
    school_extension_model_to_schema,
    team_model_to_schema,
)

hyperion_error_logger = logging.getLogger("hyperion.error")

# region: Competition Editions


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


# endregion: Competition Editions
# region: Competition Groups


async def load_memberships_by_competition_group(
    group: CompetitionGroupType,
    edition_id: UUID,
    db: AsyncSession,
) -> list[schemas_sport_competition.UserGroupMembershipComplete]:
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
        schemas_sport_competition.UserGroupMembershipComplete(
            user_id=membership.user_id,
            group=membership.group,
            edition_id=membership.edition_id,
            user=schemas_users.CoreUser(
                id=membership.user.id,
                account_type=membership.user.account_type,
                school_id=membership.user.school_id,
                email=membership.user.email,
                name=membership.user.name,
                firstname=membership.user.firstname,
                groups=[],
                school=CoreSchool(
                    id=membership.user.school.id,
                    name=membership.user.school.name,
                    email_regex=membership.user.school.email_regex,
                ),
            ),
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


# endregion: Competition Groups
# region: Competition Users


async def load_all_competition_users(
    edition_id: UUID,
    db: AsyncSession,
    exclude_non_validated: bool = False,
) -> list[schemas_sport_competition.CompetitionUser]:
    competition_users = await db.execute(
        select(models_sport_competition.CompetitionUser).where(
            models_sport_competition.CompetitionUser.edition_id == edition_id,
            models_sport_competition.CompetitionUser.validated
            if exclude_non_validated
            else and_(True),
        ),
    )
    return [
        competition_user_model_to_schema(competition_user)
        for competition_user in competition_users.scalars().all()
    ]


async def load_all_competition_users_by_school(
    school_id: UUID,
    edition_id: UUID,
    db: AsyncSession,
) -> list[schemas_sport_competition.CompetitionUser]:
    competition_users = await db.execute(
        select(models_sport_competition.CompetitionUser)
        .join(
            models_users.CoreUser,
            models_sport_competition.CompetitionUser.user_id
            == models_users.CoreUser.id,
        )
        .where(
            models_sport_competition.CompetitionUser.edition_id == edition_id,
            models_users.CoreUser.school_id == school_id,
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
                select(models_sport_competition.CompetitionUser)
                .where(
                    models_sport_competition.CompetitionUser.user_id == user_id,
                    models_sport_competition.CompetitionUser.edition_id == edition_id,
                )
                .options(
                    joinedload(
                        models_sport_competition.CompetitionUser.user,
                    ).selectinload(models_users.CoreUser.groups),
                ),
            )
        )
        .scalars()
        .first()
    )
    return competition_user_model_to_schema(user) if user else None


async def count_validated_competition_users_by_school_id(
    school_id: UUID,
    edition_id: UUID,
    db: AsyncSession,
    is_athlete: bool | None = None,
    is_cameraman: bool | None = None,
    is_pompom: bool | None = None,
    is_fanfare: bool | None = None,
) -> int:
    """
    Load the number of validated competition users for a given school in a specific edition.
    """
    result = await db.execute(
        select(func.count())
        .select_from(models_sport_competition.CompetitionUser)
        .join(
            models_users.CoreUser,
            models_sport_competition.CompetitionUser.user_id
            == models_users.CoreUser.id,
        )
        .where(
            models_users.CoreUser.school_id == school_id,
            models_sport_competition.CompetitionUser.edition_id == edition_id,
            models_sport_competition.CompetitionUser.validated,
            models_sport_competition.CompetitionUser.is_athlete == is_athlete
            if is_athlete is not None
            else and_(True),
            models_sport_competition.CompetitionUser.is_cameraman == is_cameraman
            if is_cameraman is not None
            else and_(True),
            models_sport_competition.CompetitionUser.is_pompom == is_pompom
            if is_pompom is not None
            else and_(True),
            models_sport_competition.CompetitionUser.is_fanfare == is_fanfare
            if is_fanfare is not None
            else and_(True),
        ),
    )
    return result.scalar() or 0


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


# endregion: Competition Users
# region: Schools Extensions


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
            inscription_enabled=school.inscription_enabled,
        )
        if school
        else None
    )


async def load_school_by_id(
    school_id: UUID,
    db: AsyncSession,
) -> schemas_sport_competition.SchoolExtension | None:
    school_extension = (
        (
            await db.execute(
                select(models_sport_competition.SchoolExtension)
                .where(
                    models_sport_competition.SchoolExtension.school_id == school_id,
                )
                .options(
                    selectinload(models_sport_competition.SchoolExtension.school),
                ),
            )
        )
        .scalars()
        .first()
    )
    return (
        school_extension_model_to_schema(school_extension) if school_extension else None
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


# endregion: Schools Extensions
# region: Participants


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
            certificate_file_id=participant.certificate_file_id,
            is_license_valid=participant.is_license_valid,
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


async def validate_competition_user(
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


async def invalidate_competition_user(
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
        .values(validated=False),
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


async def load_participant_by_user_id(
    user_id: str,
    edition_id: UUID,
    db: AsyncSession,
) -> schemas_sport_competition.ParticipantComplete | None:
    participant = (
        (
            await db.execute(
                select(models_sport_competition.CompetitionParticipant)
                .where(
                    models_sport_competition.CompetitionParticipant.user_id == user_id,
                    models_sport_competition.CompetitionParticipant.edition_id
                    == edition_id,
                )
                .options(
                    joinedload(
                        models_sport_competition.CompetitionParticipant.user,
                    ).selectinload(
                        models_sport_competition.CompetitionUser.user,
                    ),
                    selectinload(
                        models_sport_competition.CompetitionParticipant.team,
                    ),
                ),
            )
        )
        .scalars()
        .first()
    )
    return participant_complete_model_to_schema(participant) if participant else None


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
                    joinedload(
                        models_sport_competition.CompetitionParticipant.user,
                    ).selectinload(
                        models_sport_competition.CompetitionUser.user,
                    ),
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
            joinedload(
                models_sport_competition.CompetitionParticipant.user,
            ).selectinload(
                models_sport_competition.CompetitionUser.user,
            ),
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
                .options(
                    joinedload(
                        models_sport_competition.CompetitionParticipant.user,
                    ).selectinload(
                        models_sport_competition.CompetitionUser.user,
                    ),
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
                    joinedload(
                        models_sport_competition.CompetitionParticipant.user,
                    ).selectinload(
                        models_sport_competition.CompetitionUser.user,
                    ),
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
                    joinedload(
                        models_sport_competition.CompetitionParticipant.user,
                    ).selectinload(
                        models_sport_competition.CompetitionUser.user,
                    ),
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


async def count_validated_participants_by_school_and_sport_ids(
    school_id: UUID,
    sport_id: UUID,
    edition_id: UUID,
    db: AsyncSession,
) -> int:
    """
    Load the number of validated participants for a given school and sport in a specific edition.
    """
    result = await db.execute(
        select(func.count())
        .select_from(models_sport_competition.CompetitionParticipant)
        .join(
            models_sport_competition.CompetitionUser,
            models_sport_competition.CompetitionParticipant.user_id
            == models_sport_competition.CompetitionUser.user_id,
        )
        .where(
            models_sport_competition.CompetitionParticipant.sport_id == sport_id,
            models_sport_competition.CompetitionParticipant.edition_id == edition_id,
            models_sport_competition.CompetitionParticipant.school_id == school_id,
            models_sport_competition.CompetitionUser.validated,
        ),
    )
    return result.scalar() or 0


async def update_participant_certificate_file_id(
    user_id: str,
    sport_id: UUID,
    edition_id: UUID,
    certificate_file_id: UUID | None,
    db: AsyncSession,
) -> None:
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
        .values(certificate_file_id=certificate_file_id),
    )


async def update_participant_license_validity(
    user_id: str,
    sport_id: UUID,
    edition_id: UUID,
    is_license_valid: bool,
    db: AsyncSession,
) -> None:
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
        .values(is_license_valid=is_license_valid),
    )


# endregion: Participants
# region: Quotas


async def load_school_general_quota(
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
            athlete_cameraman_quota=quota.athlete_cameraman_quota,
            athlete_fanfare_quota=quota.athlete_fanfare_quota,
            athlete_pompom_quota=quota.athlete_pompom_quota,
            non_athlete_cameraman_quota=quota.non_athlete_cameraman_quota,
            non_athlete_fanfare_quota=quota.non_athlete_fanfare_quota,
            non_athlete_pompom_quota=quota.non_athlete_pompom_quota,
        )
        if quota
        else None
    )


async def add_school_general_quota(
    quota: schemas_sport_competition.SchoolGeneralQuota,
    db: AsyncSession,
):
    db.add(
        models_sport_competition.SchoolGeneralQuota(
            school_id=quota.school_id,
            edition_id=quota.edition_id,
            athlete_quota=quota.athlete_quota,
            cameraman_quota=quota.cameraman_quota,
            pompom_quota=quota.pompom_quota,
            fanfare_quota=quota.fanfare_quota,
            athlete_cameraman_quota=quota.athlete_cameraman_quota,
            athlete_fanfare_quota=quota.athlete_fanfare_quota,
            athlete_pompom_quota=quota.athlete_pompom_quota,
            non_athlete_cameraman_quota=quota.non_athlete_cameraman_quota,
            non_athlete_fanfare_quota=quota.non_athlete_fanfare_quota,
            non_athlete_pompom_quota=quota.non_athlete_pompom_quota,
        ),
    )
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
    quota: schemas_sport_competition.SchoolSportQuota,
    db: AsyncSession,
):
    db.add(
        models_sport_competition.SchoolSportQuota(
            sport_id=quota.sport_id,
            school_id=quota.school_id,
            edition_id=quota.edition_id,
            participant_quota=quota.participant_quota,
            team_quota=quota.team_quota,
        ),
    )
    await db.flush()


async def update_sport_quota(
    school_id: UUID,
    sport_id: UUID,
    edition_id: UUID,
    quota: schemas_sport_competition.SchoolSportQuotaEdit,
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
) -> schemas_sport_competition.SchoolSportQuota | None:
    quota = await db.get(
        models_sport_competition.SchoolSportQuota,
        (sport_id, school_id, edition_id),
    )
    return (
        schemas_sport_competition.SchoolSportQuota(
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
) -> list[schemas_sport_competition.SchoolSportQuota]:
    quotas = await db.execute(
        select(models_sport_competition.SchoolSportQuota).where(
            models_sport_competition.SchoolSportQuota.school_id == school_id,
            models_sport_competition.SchoolSportQuota.edition_id == edition_id,
        ),
    )
    return [
        schemas_sport_competition.SchoolSportQuota(
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
) -> list[schemas_sport_competition.SchoolSportQuota]:
    quotas = await db.execute(
        select(models_sport_competition.SchoolSportQuota).where(
            models_sport_competition.SchoolSportQuota.sport_id == sport_id,
            models_sport_competition.SchoolSportQuota.edition_id == edition_id,
        ),
    )
    return [
        schemas_sport_competition.SchoolSportQuota(
            school_id=quota.school_id,
            sport_id=quota.sport_id,
            edition_id=quota.edition_id,
            participant_quota=quota.participant_quota,
            team_quota=quota.team_quota,
        )
        for quota in quotas.scalars().all()
    ]


async def load_all_school_product_quotas(
    school_id: UUID,
    edition_id: UUID,
    db: AsyncSession,
) -> list[schemas_sport_competition.SchoolProductQuota]:
    products = await db.execute(
        select(models_sport_competition.SchoolProductQuota).where(
            models_sport_competition.SchoolProductQuota.school_id == school_id,
            models_sport_competition.SchoolProductQuota.edition_id == edition_id,
        ),
    )
    return [
        schemas_sport_competition.SchoolProductQuota(
            school_id=product.school_id,
            edition_id=product.edition_id,
            product_id=product.product_id,
            quota=product.quota,
        )
        for product in products.scalars().all()
    ]


async def load_school_product_quota_by_ids(
    school_id: UUID,
    product_id: UUID,
    db: AsyncSession,
) -> schemas_sport_competition.SchoolProductQuota | None:
    product = (
        (
            await db.execute(
                select(models_sport_competition.SchoolProductQuota).where(
                    models_sport_competition.SchoolProductQuota.school_id == school_id,
                    models_sport_competition.SchoolProductQuota.product_id
                    == product_id,
                ),
            )
        )
        .scalars()
        .first()
    )
    return (
        schemas_sport_competition.SchoolProductQuota(
            school_id=product.school_id,
            edition_id=product.edition_id,
            product_id=product.product_id,
            quota=product.quota,
        )
        if product
        else None
    )


async def load_all_product_quotas_by_product_id(
    product_id: UUID,
    db: AsyncSession,
) -> list[schemas_sport_competition.SchoolProductQuota]:
    products = await db.execute(
        select(models_sport_competition.SchoolProductQuota).where(
            models_sport_competition.SchoolProductQuota.product_id == product_id,
        ),
    )
    return [
        schemas_sport_competition.SchoolProductQuota(
            school_id=product.school_id,
            edition_id=product.edition_id,
            product_id=product.product_id,
            quota=product.quota,
        )
        for product in products.scalars().all()
    ]


async def add_school_product_quota(
    product_quota: schemas_sport_competition.SchoolProductQuota,
    db: AsyncSession,
):
    db.add(
        models_sport_competition.SchoolProductQuota(
            product_id=product_quota.product_id,
            school_id=product_quota.school_id,
            edition_id=product_quota.edition_id,
            quota=product_quota.quota,
        ),
    )


async def update_school_product_quota(
    school_id: UUID,
    product_id: UUID,
    product_quota: schemas_sport_competition.SchoolProductQuotaEdit,
    db: AsyncSession,
):
    await db.execute(
        update(models_sport_competition.SchoolProductQuota)
        .where(
            models_sport_competition.SchoolProductQuota.school_id == school_id,
            models_sport_competition.SchoolProductQuota.product_id == product_id,
        )
        .values(quota=product_quota.quota),
    )


async def delete_school_product_quota_by_ids(
    school_id: UUID,
    product_id: UUID,
    db: AsyncSession,
):
    await db.execute(
        delete(models_sport_competition.SchoolProductQuota).where(
            models_sport_competition.SchoolProductQuota.school_id == school_id,
            models_sport_competition.SchoolProductQuota.product_id == product_id,
        ),
    )


# endregion: Quotas
# region: Sports


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


# endregion: Sports
# region: Teams


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
        .options(selectinload(models_sport_competition.CompetitionTeam.participants)),
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


async def load_team_by_captain_id(
    captain_id: str,
    edition_id: UUID,
    db: AsyncSession,
) -> schemas_sport_competition.TeamComplete | None:
    team = (
        (
            await db.execute(
                select(models_sport_competition.CompetitionTeam).where(
                    models_sport_competition.CompetitionTeam.captain_id == captain_id,
                    models_sport_competition.CompetitionTeam.edition_id == edition_id,
                ),
            )
        )
        .scalars()
        .first()
    )
    return team_model_to_schema(team) if team else None


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
        .select_from(models_sport_competition.CompetitionTeam)
        .where(
            models_sport_competition.CompetitionTeam.school_id == school_id,
            models_sport_competition.CompetitionTeam.sport_id == sport_id,
            models_sport_competition.CompetitionTeam.edition_id == edition_id,
        ),
    )
    return result.scalar() or 0


# endregion: Teams
# region: Locations


async def add_location(
    location: schemas_sport_competition.Location,
    db: AsyncSession,
):
    db.add(
        models_sport_competition.MatchLocation(
            id=location.id,
            name=location.name,
            description=location.description,
            address=location.address,
            latitude=location.latitude,
            longitude=location.longitude,
            edition_id=location.edition_id,
        ),
    )
    await db.flush()


async def update_location(
    location_id: UUID,
    location: schemas_sport_competition.LocationEdit,
    db: AsyncSession,
):
    await db.execute(
        update(models_sport_competition.MatchLocation)
        .where(models_sport_competition.MatchLocation.id == location_id)
        .values(**location.model_dump(exclude_unset=True)),
    )
    await db.flush()


async def delete_location_by_id(
    location_id: UUID,
    db: AsyncSession,
):
    await db.execute(
        delete(models_sport_competition.MatchLocation).where(
            models_sport_competition.MatchLocation.id == location_id,
        ),
    )
    await db.flush()


async def load_location_by_id(
    location_id: UUID,
    db: AsyncSession,
) -> schemas_sport_competition.Location | None:
    location = await db.get(models_sport_competition.MatchLocation, location_id)
    return (
        schemas_sport_competition.Location(
            id=location.id,
            name=location.name,
            description=location.description,
            address=location.address,
            latitude=location.latitude,
            longitude=location.longitude,
            edition_id=location.edition_id,
        )
        if location
        else None
    )


async def load_all_locations_by_edition_id(
    edition_id: UUID,
    db: AsyncSession,
) -> list[schemas_sport_competition.Location]:
    locations = await db.execute(
        select(models_sport_competition.MatchLocation).where(
            models_sport_competition.MatchLocation.edition_id == edition_id,
        ),
    )
    return [
        schemas_sport_competition.Location(
            id=location.id,
            name=location.name,
            description=location.description,
            address=location.address,
            latitude=location.latitude,
            longitude=location.longitude,
            edition_id=location.edition_id,
        )
        for location in locations.scalars().all()
    ]


async def load_location_by_name(
    name: str,
    edition_id: UUID,
    db: AsyncSession,
) -> schemas_sport_competition.Location | None:
    location = (
        (
            await db.execute(
                select(models_sport_competition.MatchLocation).where(
                    models_sport_competition.MatchLocation.name == name,
                    models_sport_competition.MatchLocation.edition_id == edition_id,
                ),
            )
        )
        .scalars()
        .first()
    )
    return (
        schemas_sport_competition.Location(
            id=location.id,
            name=location.name,
            description=location.description,
            address=location.address,
            latitude=location.latitude,
            longitude=location.longitude,
            edition_id=location.edition_id,
        )
        if location
        else None
    )


# endregion: Locations
# region: Matches


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
) -> list[schemas_sport_competition.MatchComplete]:
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
) -> list[schemas_sport_competition.MatchComplete]:
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


async def load_all_matches_by_location_id(
    location_id: UUID,
    db: AsyncSession,
) -> list[schemas_sport_competition.MatchComplete]:
    matches = await db.execute(
        select(models_sport_competition.Match)
        .where(
            models_sport_competition.Match.location_id == location_id,
        )
        .options(
            selectinload(models_sport_competition.Match.team1),
            selectinload(models_sport_competition.Match.team2),
            selectinload(models_sport_competition.Match.location),
        ),
    )

    return [match_model_to_schema(match) for match in matches.scalars().all()]


# endregion: Matches
# region: Podiums


async def get_global_podiums(
    edition_id: UUID,
    db: AsyncSession,
) -> list[schemas_sport_competition.SchoolResult]:
    podiums = await db.execute(
        select(
            models_sport_competition.SportPodium.school_id,
            func.sum(models_sport_competition.SportPodium.points).label("points"),
        )
        .where(
            models_sport_competition.SportPodium.edition_id == edition_id,
        )
        .group_by(models_sport_competition.SportPodium.school_id),
    )
    return [
        schemas_sport_competition.SchoolResult(
            school_id=podium[0],
            total_points=podium[1],
        )
        for podium in podiums.all()
    ]


async def load_sport_podiums(
    sport_id: UUID,
    edition_id: UUID,
    db: AsyncSession,
) -> list[schemas_sport_competition.TeamSportResultComplete]:
    podiums = await db.execute(
        select(models_sport_competition.SportPodium)
        .where(
            models_sport_competition.SportPodium.sport_id == sport_id,
            models_sport_competition.SportPodium.edition_id == edition_id,
        )
        .options(
            selectinload(models_sport_competition.SportPodium.team).selectinload(
                models_sport_competition.CompetitionTeam.participants,
            ),
        ),
    )
    return [
        schemas_sport_competition.TeamSportResultComplete(
            edition_id=podium.edition_id,
            school_id=podium.school_id,
            sport_id=podium.sport_id,
            team_id=podium.team_id,
            rank=podium.rank,
            points=podium.points,
            team=team_model_to_schema(podium.team),
        )
        for podium in podiums.scalars().all()
    ]


async def load_school_podiums(
    school_id: UUID,
    edition_id: UUID,
    db: AsyncSession,
) -> list[schemas_sport_competition.TeamSportResultComplete]:
    podiums = await db.execute(
        select(models_sport_competition.SportPodium)
        .where(
            models_sport_competition.SportPodium.school_id == school_id,
            models_sport_competition.SportPodium.edition_id == edition_id,
        )
        .options(
            selectinload(models_sport_competition.SportPodium.team).selectinload(
                models_sport_competition.CompetitionTeam.participants,
            ),
        ),
    )
    return [
        schemas_sport_competition.TeamSportResultComplete(
            edition_id=podium.edition_id,
            school_id=podium.school_id,
            sport_id=podium.sport_id,
            team_id=podium.team_id,
            rank=podium.rank,
            points=podium.points,
            team=team_model_to_schema(podium.team),
        )
        for podium in podiums.scalars().all()
    ]


async def add_sport_ranking(
    rankings: list[schemas_sport_competition.TeamSportResult],
    db: AsyncSession,
):
    for ranking in rankings:
        db.add(
            models_sport_competition.SportPodium(
                school_id=ranking.school_id,
                sport_id=ranking.sport_id,
                team_id=ranking.team_id,
                edition_id=ranking.edition_id,
                rank=ranking.rank,
                points=ranking.points,
            ),
        )
    await db.flush()


async def delete_sport_ranking(
    sport_id: UUID,
    edition_id: UUID,
    db: AsyncSession,
):
    await db.execute(
        delete(models_sport_competition.SportPodium).where(
            models_sport_competition.SportPodium.sport_id == sport_id,
            models_sport_competition.SportPodium.edition_id == edition_id,
        ),
    )
    await db.flush()


# endregion: Podiums
# region: Products


async def load_products(
    edition_id: UUID,
    db: AsyncSession,
) -> list[schemas_sport_competition.ProductComplete]:
    products = await db.execute(
        select(models_sport_competition.CompetitionProduct)
        .where(
            models_sport_competition.CompetitionProduct.edition_id == edition_id,
        )
        .options(
            selectinload(models_sport_competition.CompetitionProduct.variants),
        ),
    )
    return [
        schemas_sport_competition.ProductComplete(
            id=product.id,
            edition_id=product.edition_id,
            name=product.name,
            required=product.required,
            description=product.description,
            variants=[
                schemas_sport_competition.ProductVariant(
                    id=variant.id,
                    edition_id=variant.edition_id,
                    product_id=variant.product_id,
                    name=variant.name,
                    description=variant.description,
                    price=variant.price,
                    enabled=variant.enabled,
                    unique=variant.unique,
                    school_type=variant.school_type,
                    public_type=variant.public_type,
                )
                for variant in product.variants
            ],
        )
        for product in products.scalars().all()
    ]


async def load_product_by_id(
    product_id: UUID,
    db: AsyncSession,
) -> schemas_sport_competition.ProductComplete | None:
    product = await db.get(models_sport_competition.CompetitionProduct, product_id)
    return (
        schemas_sport_competition.ProductComplete(
            id=product.id,
            edition_id=product.edition_id,
            name=product.name,
            required=product.required,
            description=product.description,
        )
        if product
        else None
    )


async def load_required_products(
    edition_id: UUID,
    db: AsyncSession,
) -> list[schemas_sport_competition.Product]:
    products = await db.execute(
        select(models_sport_competition.CompetitionProduct).where(
            models_sport_competition.CompetitionProduct.edition_id == edition_id,
            models_sport_competition.CompetitionProduct.required,
        ),
    )
    return [
        schemas_sport_competition.Product(
            id=product.id,
            edition_id=product.edition_id,
            name=product.name,
            description=product.description,
        )
        for product in products.scalars().all()
    ]


async def add_product(
    product: schemas_sport_competition.Product,
    db: AsyncSession,
):
    db.add(
        models_sport_competition.CompetitionProduct(
            id=product.id,
            edition_id=product.edition_id,
            name=product.name,
            required=product.required,
            description=product.description,
        ),
    )
    await db.flush()


async def update_product(
    product_id: UUID,
    product: schemas_sport_competition.ProductEdit,
    db: AsyncSession,
):
    await db.execute(
        update(models_sport_competition.CompetitionProduct)
        .where(models_sport_competition.CompetitionProduct.id == product_id)
        .values(**product.model_dump(exclude_unset=True)),
    )
    await db.flush()


async def delete_product_by_id(
    product_id: UUID,
    db: AsyncSession,
):
    await db.execute(
        delete(models_sport_competition.CompetitionProduct).where(
            models_sport_competition.CompetitionProduct.id == product_id,
        ),
    )
    await db.flush()


# endregion: Products
# region: Product Variants


async def load_product_variants(
    product_id: UUID,
    db: AsyncSession,
) -> list[schemas_sport_competition.ProductVariant]:
    variants = await db.execute(
        select(models_sport_competition.CompetitionProductVariant).where(
            models_sport_competition.CompetitionProductVariant.product_id == product_id,
        ),
    )
    return [
        schemas_sport_competition.ProductVariant(
            id=variant.id,
            edition_id=variant.edition_id,
            product_id=variant.product_id,
            name=variant.name,
            description=variant.description,
            price=variant.price,
            enabled=variant.enabled,
            unique=variant.unique,
            school_type=variant.school_type,
            public_type=variant.public_type,
        )
        for variant in variants.scalars().all()
    ]


async def load_available_product_variants(
    edition_id: UUID,
    school_type: ProductSchoolType,
    public_type: list[ProductPublicType],
    db: AsyncSession,
) -> list[schemas_sport_competition.ProductVariantComplete]:
    variants = await db.execute(
        select(models_sport_competition.CompetitionProductVariant).where(
            models_sport_competition.CompetitionProductVariant.edition_id == edition_id,
            models_sport_competition.CompetitionProductVariant.enabled,
            models_sport_competition.CompetitionProductVariant.school_type
            == school_type,
            or_(
                models_sport_competition.CompetitionProductVariant.public_type.in_(
                    public_type,
                ),
                models_sport_competition.CompetitionProductVariant.public_type.is_(
                    None,
                ),
            ),
        ),
    )
    return [
        schemas_sport_competition.ProductVariantComplete(
            id=variant.id,
            edition_id=variant.edition_id,
            product_id=variant.product_id,
            name=variant.name,
            description=variant.description,
            price=variant.price,
            enabled=variant.enabled,
            unique=variant.unique,
            school_type=variant.school_type,
            public_type=variant.public_type,
            product=schemas_sport_competition.Product(
                id=variant.product.id,
                edition_id=variant.product.edition_id,
                name=variant.product.name,
                description=variant.product.description,
                required=variant.product.required,
            ),
        )
        for variant in variants.scalars().all()
    ]


async def load_product_variant_by_id(
    variant_id: UUID,
    db: AsyncSession,
) -> schemas_sport_competition.ProductVariantComplete | None:
    variant = await db.get(
        models_sport_competition.CompetitionProductVariant,
        variant_id,
    )
    return (
        schemas_sport_competition.ProductVariantComplete(
            id=variant.id,
            edition_id=variant.edition_id,
            product_id=variant.product_id,
            name=variant.name,
            description=variant.description,
            price=variant.price,
            enabled=variant.enabled,
            unique=variant.unique,
            school_type=variant.school_type,
            public_type=variant.public_type,
            product=schemas_sport_competition.Product(
                id=variant.product.id,
                edition_id=variant.product.edition_id,
                name=variant.product.name,
                description=variant.product.description,
                required=variant.product.required,
            ),
        )
        if variant
        else None
    )


async def add_product_variant(
    variant: schemas_sport_competition.ProductVariant,
    db: AsyncSession,
):
    db.add(
        models_sport_competition.CompetitionProductVariant(
            id=variant.id,
            edition_id=variant.edition_id,
            product_id=variant.product_id,
            name=variant.name,
            description=variant.description,
            price=variant.price,
            enabled=variant.enabled,
            unique=variant.unique,
            school_type=variant.school_type,
            public_type=variant.public_type,
        ),
    )
    await db.flush()


async def update_product_variant(
    variant_id: UUID,
    variant: schemas_sport_competition.ProductVariantEdit,
    db: AsyncSession,
):
    await db.execute(
        update(models_sport_competition.CompetitionProductVariant)
        .where(models_sport_competition.CompetitionProductVariant.id == variant_id)
        .values(**variant.model_dump(exclude_unset=True)),
    )
    await db.flush()


async def delete_product_variant_by_id(
    variant_id: UUID,
    db: AsyncSession,
):
    await db.execute(
        delete(models_sport_competition.CompetitionProductVariant).where(
            models_sport_competition.CompetitionProductVariant.id == variant_id,
        ),
    )
    await db.flush()


# endregion: Product Variants
# region: Purchases


async def load_all_purchases(
    edition_id: UUID,
    db: AsyncSession,
) -> dict[str, list[schemas_sport_competition.PurchaseComplete]]:
    purchases = await db.execute(
        select(models_sport_competition.CompetitionPurchase)
        .where(
            models_sport_competition.CompetitionPurchase.edition_id == edition_id,
        )
        .options(
            selectinload(models_sport_competition.CompetitionPurchase.product_variant),
        ),
    )
    users_purchases: dict[str, list[schemas_sport_competition.PurchaseComplete]] = {}
    for purchase in purchases.scalars().all():
        if purchase.user_id not in users_purchases:
            users_purchases[purchase.user_id] = []
        users_purchases[purchase.user_id].append(purchase_model_to_schema(purchase))
    return users_purchases


async def load_purchases_by_user_id(
    user_id: str,
    edition_id: UUID,
    db: AsyncSession,
) -> list[schemas_sport_competition.PurchaseComplete]:
    purchases = await db.execute(
        select(models_sport_competition.CompetitionPurchase)
        .where(
            models_sport_competition.CompetitionPurchase.user_id == user_id,
            models_sport_competition.CompetitionPurchase.edition_id == edition_id,
        )
        .options(
            selectinload(models_sport_competition.CompetitionPurchase.product_variant),
        ),
    )
    return [
        purchase_model_to_schema(purchase) for purchase in purchases.scalars().all()
    ]


async def load_purchase_by_ids(
    user_id: str,
    product_variant_id: UUID,
    db: AsyncSession,
) -> schemas_sport_competition.Purchase | None:
    purchase = (
        (
            await db.execute(
                select(models_sport_competition.CompetitionPurchase)
                .where(
                    models_sport_competition.CompetitionPurchase.user_id == user_id,
                    models_sport_competition.CompetitionPurchase.product_variant_id
                    == product_variant_id,
                )
                .options(
                    selectinload(
                        models_sport_competition.CompetitionPurchase.product_variant,
                    ),
                ),
            )
        )
        .scalars()
        .first()
    )
    return purchase_model_to_schema(purchase) if purchase else None


async def load_purchases_by_variant_id(
    variant_id: UUID,
    db: AsyncSession,
) -> list[schemas_sport_competition.PurchaseComplete]:
    purchases = await db.execute(
        select(models_sport_competition.CompetitionPurchase)
        .where(
            models_sport_competition.CompetitionPurchase.product_variant_id
            == variant_id,
        )
        .options(
            selectinload(models_sport_competition.CompetitionPurchase.product_variant),
        ),
    )
    return [
        purchase_model_to_schema(purchase) for purchase in purchases.scalars().all()
    ]


async def count_validated_purchases_by_product_id_and_school_id(
    product_id: UUID,
    school_id: UUID,
    db: AsyncSession,
) -> int:
    result = await db.execute(
        select(func.count())
        .select_from(models_sport_competition.CompetitionPurchase)
        .join(
            models_sport_competition.CompetitionProductVariant,
            models_sport_competition.CompetitionPurchase.product_variant_id
            == models_sport_competition.CompetitionProductVariant.id,
        )
        .join(
            models_sport_competition.CompetitionUser,
            models_sport_competition.CompetitionPurchase.user_id
            == models_sport_competition.CompetitionUser.user_id,
        )
        .join(
            models_users.CoreUser,
            models_sport_competition.CompetitionUser.user_id
            == models_users.CoreUser.id,
        )
        .where(
            models_sport_competition.CompetitionProductVariant.product_id == product_id,
            models_users.CoreUser.school_id == school_id,
            models_sport_competition.CompetitionUser.validated,
        ),
    )
    return result.scalar() or 0


async def add_purchase(
    purchase: schemas_sport_competition.Purchase,
    db: AsyncSession,
):
    db.add(
        models_sport_competition.CompetitionPurchase(
            user_id=purchase.user_id,
            product_variant_id=purchase.product_variant_id,
            edition_id=purchase.edition_id,
            quantity=purchase.quantity,
            purchased_on=purchase.purchased_on,
            validated=purchase.validated,
        ),
    )
    await db.flush()


async def update_purchase(
    user_id: str,
    product_variant_id: UUID,
    purchase: schemas_sport_competition.PurchaseEdit,
    db: AsyncSession,
):
    await db.execute(
        update(models_sport_competition.CompetitionPurchase)
        .where(
            models_sport_competition.CompetitionPurchase.user_id == user_id,
            models_sport_competition.CompetitionPurchase.product_variant_id
            == product_variant_id,
        )
        .values(**purchase.model_dump(exclude_unset=True)),
    )
    await db.flush()


async def mark_purchase_as_validated(
    user_id: str,
    product_variant_id: UUID,
    validated: bool,
    db: AsyncSession,
):
    await db.execute(
        update(models_sport_competition.CompetitionPurchase)
        .where(
            models_sport_competition.CompetitionPurchase.user_id == user_id,
            models_sport_competition.CompetitionPurchase.product_variant_id
            == product_variant_id,
        )
        .values(validated=validated),
    )


async def delete_purchase(
    user_id: str,
    product_variant_id: UUID,
    db: AsyncSession,
):
    await db.execute(
        delete(models_sport_competition.CompetitionPurchase).where(
            models_sport_competition.CompetitionPurchase.user_id == user_id,
            models_sport_competition.CompetitionPurchase.product_variant_id
            == product_variant_id,
        ),
    )
    await db.flush()


# endregion: Purchases
# region: Payments


async def load_all_payments(
    edition_id: UUID,
    db: AsyncSession,
) -> dict[str, list[schemas_sport_competition.PaymentComplete]]:
    payments = await db.execute(
        select(models_sport_competition.CompetitionPayment).where(
            models_sport_competition.CompetitionPayment.edition_id == edition_id,
        ),
    )
    users_payments: dict[str, list[schemas_sport_competition.PaymentComplete]] = {}
    for payment in payments.scalars().all():
        if payment.user_id not in users_payments:
            users_payments[payment.user_id] = []
        users_payments[payment.user_id].append(
            schemas_sport_competition.PaymentComplete(
                id=payment.id,
                user_id=payment.user_id,
                edition_id=payment.edition_id,
                total=payment.total,
            ),
        )
    return users_payments


async def load_user_payments(
    user_id: str,
    edition_id: UUID,
    db: AsyncSession,
) -> list[schemas_sport_competition.PaymentComplete]:
    payments = await db.execute(
        select(models_sport_competition.CompetitionPayment).where(
            models_sport_competition.CompetitionPayment.user_id == user_id,
            models_sport_competition.CompetitionPayment.edition_id == edition_id,
        ),
    )
    return [
        schemas_sport_competition.PaymentComplete(
            id=payment.id,
            user_id=payment.user_id,
            edition_id=payment.edition_id,
            total=payment.total,
        )
        for payment in payments.scalars().all()
    ]


async def load_payment_by_id(
    payment_id: UUID,
    db: AsyncSession,
) -> schemas_sport_competition.PaymentComplete | None:
    payment = await db.get(models_sport_competition.CompetitionPayment, payment_id)
    return (
        schemas_sport_competition.PaymentComplete(
            id=payment.id,
            user_id=payment.user_id,
            edition_id=payment.edition_id,
            total=payment.total,
        )
        if payment
        else None
    )


async def add_payment(
    payment: schemas_sport_competition.PaymentComplete,
    db: AsyncSession,
):
    db.add(
        models_sport_competition.CompetitionPayment(
            id=payment.id,
            user_id=payment.user_id,
            edition_id=payment.edition_id,
            total=payment.total,
            created_at=datetime.now(UTC),
        ),
    )


async def delete_payment(
    payment_id: UUID,
    db: AsyncSession,
):
    await db.execute(
        delete(models_sport_competition.CompetitionPayment).where(
            models_sport_competition.CompetitionPayment.id == payment_id,
        ),
    )
    await db.flush()


# endregion: Payments
# region: Checkouts


def add_checkout(
    db: AsyncSession,
    checkout: schemas_sport_competition.Checkout,
):
    db.add(
        models_sport_competition.CompetitionCheckout(
            id=checkout.id,
            user_id=checkout.user_id,
            edition_id=checkout.edition_id,
            checkout_id=checkout.checkout_id,
        ),
    )


async def get_checkout_by_checkout_id(
    checkout_id: UUID,
    db: AsyncSession,
) -> schemas_sport_competition.Checkout | None:
    checkout = (
        (
            await db.execute(
                select(models_sport_competition.CompetitionCheckout).where(
                    models_sport_competition.CompetitionCheckout.checkout_id
                    == checkout_id,
                ),
            )
        )
        .scalars()
        .first()
    )
    return (
        schemas_sport_competition.Checkout(
            id=checkout.id,
            user_id=checkout.user_id,
            edition_id=checkout.edition_id,
            checkout_id=checkout.checkout_id,
        )
        if checkout
        else None
    )


# endregion: Checkouts
# region: Volunteers Shifts


async def load_all_volunteer_shifts_by_edition_id(
    edition_id: UUID,
    db: AsyncSession,
) -> list[schemas_sport_competition.VolunteerShiftComplete]:
    shifts = await db.execute(
        select(models_sport_competition.VolunteerShift)
        .where(
            models_sport_competition.VolunteerShift.edition_id == edition_id,
        )
        .options(
            selectinload(
                models_sport_competition.VolunteerShift.registrations,
            ).selectinload(
                models_sport_competition.VolunteerRegistration.user,
            ),
        ),
    )
    return [
        schemas_sport_competition.VolunteerShiftComplete(
            id=shift.id,
            edition_id=shift.edition_id,
            name=shift.name,
            description=shift.description,
            value=shift.value,
            start_time=shift.start_time,
            end_time=shift.end_time,
            max_volunteers=shift.max_volunteers,
            location=shift.location,
            registrations=[
                schemas_sport_competition.VolunteerRegistrationWithUser(
                    user_id=registration.user_id,
                    shift_id=registration.shift_id,
                    edition_id=registration.edition_id,
                    validated=registration.validated,
                    registered_at=registration.registered_at,
                    user=competition_user_model_to_schema(registration.user),
                )
                for registration in shift.registrations
            ],
        )
        for shift in shifts.scalars().all()
    ]


async def load_volunteer_shift_by_id(
    shift_id: UUID,
    db: AsyncSession,
) -> schemas_sport_competition.VolunteerShiftComplete | None:
    shift = (
        (
            await db.execute(
                select(models_sport_competition.VolunteerShift)
                .where(
                    models_sport_competition.VolunteerShift.id == shift_id,
                )
                .options(
                    selectinload(
                        models_sport_competition.VolunteerShift.registrations,
                    ).selectinload(
                        models_sport_competition.VolunteerRegistration.user,
                    ),
                ),
            )
        )
        .scalars()
        .first()
    )
    return (
        schemas_sport_competition.VolunteerShiftComplete(
            id=shift.id,
            edition_id=shift.edition_id,
            name=shift.name,
            description=shift.description,
            value=shift.value,
            start_time=shift.start_time,
            end_time=shift.end_time,
            max_volunteers=shift.max_volunteers,
            location=shift.location,
            registrations=[
                schemas_sport_competition.VolunteerRegistrationWithUser(
                    user_id=registration.user_id,
                    shift_id=registration.shift_id,
                    edition_id=registration.edition_id,
                    validated=registration.validated,
                    registered_at=registration.registered_at,
                    user=competition_user_model_to_schema(registration.user),
                )
                for registration in shift.registrations
            ],
        )
        if shift
        else None
    )


async def add_volunteer_shift(
    shift: schemas_sport_competition.VolunteerShift,
    db: AsyncSession,
):
    db.add(
        models_sport_competition.VolunteerShift(
            id=shift.id,
            edition_id=shift.edition_id,
            name=shift.name,
            description=shift.description,
            value=shift.value,
            start_time=shift.start_time,
            end_time=shift.end_time,
            max_volunteers=shift.max_volunteers,
            location=shift.location,
        ),
    )


async def update_volunteer_shift(
    shift_id: UUID,
    shift: schemas_sport_competition.VolunteerShiftEdit,
    db: AsyncSession,
):
    await db.execute(
        update(models_sport_competition.VolunteerShift)
        .where(models_sport_competition.VolunteerShift.id == shift_id)
        .values(**shift.model_dump(exclude_unset=True)),
    )


async def delete_volunteer_shift_by_id(
    shift_id: UUID,
    db: AsyncSession,
):
    await db.execute(
        delete(models_sport_competition.VolunteerShift).where(
            models_sport_competition.VolunteerShift.id == shift_id,
        ),
    )


# endregion: Volunteers Shifts
# region: Volunteers Registrations


async def load_volunteer_registrations_by_user_id(
    user_id: str,
    edition_id: UUID,
    db: AsyncSession,
) -> list[schemas_sport_competition.VolunteerRegistrationComplete]:
    registrations = await db.execute(
        select(models_sport_competition.VolunteerRegistration)
        .where(
            models_sport_competition.VolunteerRegistration.user_id == user_id,
            models_sport_competition.VolunteerRegistration.edition_id == edition_id,
        )
        .options(
            selectinload(models_sport_competition.VolunteerRegistration.shift),
        ),
    )
    return [
        schemas_sport_competition.VolunteerRegistrationComplete(
            user_id=registration.user_id,
            shift_id=registration.shift_id,
            edition_id=registration.edition_id,
            validated=registration.validated,
            registered_at=registration.registered_at,
            shift=schemas_sport_competition.VolunteerShift(
                id=registration.shift.id,
                edition_id=registration.shift.edition_id,
                name=registration.shift.name,
                description=registration.shift.description,
                value=registration.shift.value,
                start_time=registration.shift.start_time,
                end_time=registration.shift.end_time,
                max_volunteers=registration.shift.max_volunteers,
                location=registration.shift.location,
            )
            if registration.shift
            else None,
        )
        for registration in registrations.scalars().all()
    ]


async def add_volunteer_registration(
    registration: schemas_sport_competition.VolunteerRegistration,
    db: AsyncSession,
):
    db.add(
        models_sport_competition.VolunteerRegistration(
            user_id=registration.user_id,
            shift_id=registration.shift_id,
            edition_id=registration.edition_id,
            validated=registration.validated,
            registered_at=registration.registered_at,
        ),
    )


async def delete_volunteer_registration(
    user_id: str,
    shift_id: UUID,
    db: AsyncSession,
):
    await db.execute(
        delete(models_sport_competition.VolunteerRegistration).where(
            models_sport_competition.VolunteerRegistration.user_id == user_id,
            models_sport_competition.VolunteerRegistration.shift_id == shift_id,
        ),
    )


async def delete_volunteer_registrations_for_shift(
    shift_id: UUID,
    db: AsyncSession,
):
    await db.execute(
        delete(models_sport_competition.VolunteerRegistration).where(
            models_sport_competition.VolunteerRegistration.shift_id == shift_id,
        ),
    )
