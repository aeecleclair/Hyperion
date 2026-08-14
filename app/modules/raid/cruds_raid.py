from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.raid import models_raid, schemas_raid
from app.modules.raid.raid_type import (
    Difficulty,
    DocumentValidation,
    RaidRegistrationStatus,
)


async def create_participant(
    participant: models_raid.RaidParticipant,
    db: AsyncSession,
) -> models_raid.RaidParticipant:
    db.add(participant)
    await db.flush()
    return participant


async def get_all_participants(
    edition_id: UUID,
    db: AsyncSession,
    status: RaidRegistrationStatus | None = None,
) -> Sequence[models_raid.RaidParticipant]:
    stmt = (
        select(models_raid.RaidParticipant)
        .where(models_raid.RaidParticipant.edition_id == edition_id)
        .options(selectinload("*"))
    )
    if status is not None:
        stmt = stmt.where(models_raid.RaidParticipant.status == status)
    participants = await db.execute(stmt)
    return participants.scalars().all()


async def update_participant(
    user_id: str,
    edition_id: UUID,
    values: dict,
    db: AsyncSession,
) -> None:
    if not values:
        return
    await db.execute(
        update(models_raid.RaidParticipant)
        .where(
            models_raid.RaidParticipant.user_id == user_id,
            models_raid.RaidParticipant.edition_id == edition_id,
        )
        .values(**values),
    )
    await db.flush()


async def update_participant_minority(
    user_id: str,
    edition_id: UUID,
    is_minor: bool,
    db: AsyncSession,
) -> None:
    await db.execute(
        update(models_raid.RaidParticipant)
        .where(
            models_raid.RaidParticipant.user_id == user_id,
            models_raid.RaidParticipant.edition_id == edition_id,
        )
        .values(is_minor=is_minor),
    )
    await db.flush()


async def update_participant_status(
    user_id: str,
    edition_id: UUID,
    status: RaidRegistrationStatus,
    db: AsyncSession,
) -> None:
    await db.execute(
        update(models_raid.RaidParticipant)
        .where(
            models_raid.RaidParticipant.user_id == user_id,
            models_raid.RaidParticipant.edition_id == edition_id,
        )
        .values(status=status),
    )
    await db.flush()


async def is_user_a_participant(
    user_id: str,
    edition_id: UUID,
    db: AsyncSession,
) -> bool:
    result = await db.execute(
        select(models_raid.RaidParticipant.user_id).where(
            models_raid.RaidParticipant.user_id == user_id,
            models_raid.RaidParticipant.edition_id == edition_id,
        ),
    )
    return result.first() is not None


async def get_team_by_participant_id(
    user_id: str,
    edition_id: UUID,
    db: AsyncSession,
) -> models_raid.RaidTeam | None:
    team = await db.execute(
        select(models_raid.RaidTeam)
        .where(
            models_raid.RaidTeam.edition_id == edition_id,
            or_(
                models_raid.RaidTeam.captain_id == user_id,
                models_raid.RaidTeam.second_id == user_id,
            ),
        )
        .options(selectinload("*")),
    )
    return team.scalars().first()


async def get_all_teams(
    edition_id: UUID,
    db: AsyncSession,
) -> Sequence[models_raid.RaidTeam]:
    teams = await db.execute(
        select(models_raid.RaidTeam)
        .where(models_raid.RaidTeam.edition_id == edition_id)
        .options(selectinload("*")),
    )
    return teams.scalars().all()


async def get_all_validated_teams(
    edition_id: UUID,
    db: AsyncSession,
) -> Sequence[models_raid.RaidTeam]:
    """Validated = captain AND second both have status=validated."""
    Captain = models_raid.RaidParticipant.__table__.alias("captain_p")
    Second = models_raid.RaidParticipant.__table__.alias("second_p")
    stmt = (
        select(models_raid.RaidTeam)
        .where(models_raid.RaidTeam.edition_id == edition_id)
        .join(
            Captain,
            (Captain.c.user_id == models_raid.RaidTeam.captain_id)
            & (Captain.c.edition_id == models_raid.RaidTeam.edition_id),
        )
        .join(
            Second,
            (Second.c.user_id == models_raid.RaidTeam.second_id)
            & (Second.c.edition_id == models_raid.RaidTeam.edition_id),
        )
        .where(
            Captain.c.status == RaidRegistrationStatus.validated,
            Second.c.status == RaidRegistrationStatus.validated,
        )
        .options(selectinload("*"))
    )
    teams = await db.execute(stmt)
    return teams.scalars().all()


async def get_team_by_id(
    team_id: str,
    db: AsyncSession,
) -> models_raid.RaidTeam | None:
    team = await db.execute(
        select(models_raid.RaidTeam)
        .where(models_raid.RaidTeam.id == team_id)
        .options(selectinload("*")),
    )
    return team.scalars().first()


async def create_team(
    team: models_raid.RaidTeam,
    db: AsyncSession,
) -> None:
    db.add(team)
    await db.flush()


async def update_team(
    team_id: str,
    team: schemas_raid.RaidTeamUpdate,
    db: AsyncSession,
) -> None:
    values = team.model_dump(exclude_none=True)
    if not values:
        return
    await db.execute(
        update(models_raid.RaidTeam)
        .where(models_raid.RaidTeam.id == team_id)
        .values(**values),
    )
    await db.flush()


async def update_team_captain_id(
    team_id: str,
    captain_id: str,
    db: AsyncSession,
) -> None:
    await db.execute(
        update(models_raid.RaidTeam)
        .where(models_raid.RaidTeam.id == team_id)
        .values(captain_id=captain_id),
    )
    await db.flush()


async def update_team_second_id(
    team_id: str,
    second_id: str | None,
    db: AsyncSession,
) -> None:
    await db.execute(
        update(models_raid.RaidTeam)
        .where(models_raid.RaidTeam.id == team_id)
        .values(second_id=second_id),
    )
    await db.flush()


async def delete_participant(
    user_id: str,
    edition_id: UUID,
    db: AsyncSession,
) -> None:
    await db.execute(
        delete(models_raid.RaidParticipant).where(
            models_raid.RaidParticipant.user_id == user_id,
            models_raid.RaidParticipant.edition_id == edition_id,
        ),
    )
    await db.flush()


async def delete_all_participant(
    edition_id: UUID,
    db: AsyncSession,
) -> None:
    await db.execute(
        delete(models_raid.RaidParticipant).where(
            models_raid.RaidParticipant.edition_id == edition_id,
        ),
    )
    await db.flush()


async def delete_team_invite_tokens(
    team_id: str,
    db: AsyncSession,
) -> None:
    await db.execute(
        delete(models_raid.InviteToken).where(
            models_raid.InviteToken.team_id == team_id,
        ),
    )
    await db.flush()


async def delete_all_invite_tokens(
    edition_id: UUID,
    db: AsyncSession,
) -> None:
    await db.execute(
        delete(models_raid.InviteToken).where(
            models_raid.InviteToken.edition_id == edition_id,
        ),
    )
    await db.flush()


async def delete_team(
    team_id: str,
    db: AsyncSession,
) -> None:
    await db.execute(
        delete(models_raid.RaidTeam).where(models_raid.RaidTeam.id == team_id),
    )
    await db.flush()


async def delete_all_teams(
    edition_id: UUID,
    db: AsyncSession,
) -> None:
    await db.execute(
        delete(models_raid.RaidTeam).where(
            models_raid.RaidTeam.edition_id == edition_id,
        ),
    )
    await db.flush()


async def add_security_file(
    security_file: models_raid.SecurityFile,
    db: AsyncSession,
) -> models_raid.SecurityFile:
    db.add(security_file)
    await db.flush()
    return security_file


async def delete_security_file(
    security_file_id: str,
    db: AsyncSession,
) -> None:
    await db.execute(
        delete(models_raid.SecurityFile).where(
            models_raid.SecurityFile.id == security_file_id,
        ),
    )
    await db.flush()


async def update_security_file(
    security_file_id: str,
    security_file: schemas_raid.SecurityFileBase,
    db: AsyncSession,
) -> None:
    await db.execute(
        update(models_raid.SecurityFile)
        .where(models_raid.SecurityFile.id == security_file_id)
        .values(**security_file.model_dump(exclude_none=True)),
    )
    await db.flush()


async def update_security_file_id(
    security_file_id: str,
    file_id: str,
    db: AsyncSession,
) -> None:
    await db.execute(
        update(models_raid.SecurityFile)
        .where(models_raid.SecurityFile.id == security_file_id)
        .values(file_id=file_id),
    )
    await db.flush()


async def assign_security_file(
    user_id: str,
    edition_id: UUID,
    security_file_id: str,
    db: AsyncSession,
) -> None:
    await db.execute(
        update(models_raid.RaidParticipant)
        .where(
            models_raid.RaidParticipant.user_id == user_id,
            models_raid.RaidParticipant.edition_id == edition_id,
        )
        .values(security_file_id=security_file_id),
    )
    await db.flush()


async def create_document(
    document: models_raid.Document,
    db: AsyncSession,
) -> models_raid.Document:
    db.add(document)
    await db.flush()
    return document


async def assign_document(
    user_id: str,
    edition_id: UUID,
    document_id: str | None,
    document_key: str,
    db: AsyncSession,
) -> None:
    await db.execute(
        update(models_raid.RaidParticipant)
        .where(
            models_raid.RaidParticipant.user_id == user_id,
            models_raid.RaidParticipant.edition_id == edition_id,
        )
        .values({document_key: document_id}),
    )
    await db.flush()


async def update_document_validation(
    document_id: str,
    validation: DocumentValidation,
    db: AsyncSession,
) -> None:
    await db.execute(
        update(models_raid.Document)
        .where(models_raid.Document.id == document_id)
        .values(validation=validation),
    )
    await db.flush()


async def get_document_by_id(
    document_id: str,
    db: AsyncSession,
) -> models_raid.Document | None:
    document = await db.execute(
        select(models_raid.Document).where(models_raid.Document.id == document_id),
    )
    return document.scalars().first()


async def get_user_by_document_id(
    document_id: str,
    db: AsyncSession,
) -> models_raid.RaidParticipant | None:
    document = await db.execute(
        select(models_raid.RaidParticipant).where(
            or_(
                models_raid.RaidParticipant.id_card_id == document_id,
                models_raid.RaidParticipant.medical_certificate_id == document_id,
                models_raid.RaidParticipant.student_card_id == document_id,
                models_raid.RaidParticipant.raid_rules_id == document_id,
                models_raid.RaidParticipant.parent_authorization_id == document_id,
            ),
        ),
    )
    return document.scalars().first()


async def upload_document(
    document: models_raid.Document,
    db: AsyncSession,
) -> models_raid.Document:
    db.add(document)
    await db.flush()
    return document


async def update_document(
    document_id: str,
    document: schemas_raid.DocumentUpdate,
    db: AsyncSession,
) -> None:
    await db.execute(
        update(models_raid.Document)
        .where(models_raid.Document.id == document_id)
        .values(**document.model_dump(exclude_none=True)),
    )
    await db.flush()


async def mark_document_as_newly_updated(
    document_id: str,
    db: AsyncSession,
):
    await db.execute(
        update(models_raid.Document)
        .where(models_raid.Document.id == document_id)
        .values(uploaded_at=datetime.now(tz=UTC).date(), validation="pending"),
    )
    await db.flush()


async def confirm_payment(
    user_id: str,
    edition_id: UUID,
    db: AsyncSession,
) -> None:
    await db.execute(
        update(models_raid.RaidParticipant)
        .where(
            models_raid.RaidParticipant.user_id == user_id,
            models_raid.RaidParticipant.edition_id == edition_id,
        )
        .values(payment=True),
    )
    await db.flush()


async def confirm_t_shirt_payment(
    user_id: str,
    edition_id: UUID,
    db: AsyncSession,
) -> None:
    await db.execute(
        update(models_raid.RaidParticipant)
        .where(
            models_raid.RaidParticipant.user_id == user_id,
            models_raid.RaidParticipant.edition_id == edition_id,
        )
        .values(t_shirt_payment=True),
    )
    await db.flush()


async def validate_attestation_on_honour(
    user_id: str,
    edition_id: UUID,
    db: AsyncSession,
) -> None:
    await db.execute(
        update(models_raid.RaidParticipant)
        .where(
            models_raid.RaidParticipant.user_id == user_id,
            models_raid.RaidParticipant.edition_id == edition_id,
        )
        .values(attestation_on_honour=True),
    )
    await db.flush()


async def get_participant_by_user_id(
    user_id: str,
    edition_id: UUID,
    db: AsyncSession,
) -> models_raid.RaidParticipant | None:
    participant = await db.execute(
        select(models_raid.RaidParticipant)
        .where(
            models_raid.RaidParticipant.user_id == user_id,
            models_raid.RaidParticipant.edition_id == edition_id,
        )
        .options(selectinload("*")),
    )
    return participant.scalars().first()


async def get_number_of_teams(
    edition_id: UUID,
    db: AsyncSession,
) -> int:
    result = await db.execute(
        select(func.count())
        .select_from(models_raid.RaidTeam)
        .where(models_raid.RaidTeam.edition_id == edition_id),
    )
    return result.scalar() or 0


async def get_security_file_by_security_id(
    security_id: str,
    db: AsyncSession,
) -> models_raid.SecurityFile | None:
    security_file = await db.execute(
        select(models_raid.SecurityFile).where(
            models_raid.SecurityFile.id == security_id,
        ),
    )
    return security_file.scalars().first()


async def create_invite_token(
    invite: models_raid.InviteToken,
    db: AsyncSession,
) -> models_raid.InviteToken:
    db.add(invite)
    await db.flush()
    return invite


async def get_invite_token_by_team_id(
    team_id: str,
    db: AsyncSession,
) -> models_raid.InviteToken | None:
    invite = await db.execute(
        select(models_raid.InviteToken).where(
            models_raid.InviteToken.team_id == team_id,
        ),
    )
    return invite.scalars().first()


async def get_invite_token_by_token(
    token: str,
    db: AsyncSession,
) -> models_raid.InviteToken | None:
    invite = await db.execute(
        select(models_raid.InviteToken).where(models_raid.InviteToken.token == token),
    )
    return invite.scalars().first()


async def delete_invite_token(
    token_id: str,
    db: AsyncSession,
) -> None:
    await db.execute(
        delete(models_raid.InviteToken).where(models_raid.InviteToken.id == token_id),
    )
    await db.flush()


async def update_team_file_id(
    team_id: str,
    file_id: str,
    db: AsyncSession,
) -> None:
    await db.execute(
        update(models_raid.RaidTeam)
        .where(models_raid.RaidTeam.id == team_id)
        .values(file_id=file_id),
    )
    await db.flush()


async def get_max_team_number_by_difficulty(
    difficulty: Difficulty,
    edition_id: UUID,
    db: AsyncSession,
) -> int:
    """Returns the highest team number among validated teams for a difficulty.

    Validated = both captain and second have status=validated.
    """
    Captain = models_raid.RaidParticipant.__table__.alias("captain_p")
    Second = models_raid.RaidParticipant.__table__.alias("second_p")
    stmt = (
        select(func.max(models_raid.RaidTeam.number))
        .where(
            models_raid.RaidTeam.edition_id == edition_id,
            models_raid.RaidTeam.difficulty == difficulty,
        )
        .join(
            Captain,
            (Captain.c.user_id == models_raid.RaidTeam.captain_id)
            & (Captain.c.edition_id == models_raid.RaidTeam.edition_id),
        )
        .join(
            Second,
            (Second.c.user_id == models_raid.RaidTeam.second_id)
            & (Second.c.edition_id == models_raid.RaidTeam.edition_id),
        )
        .where(
            Captain.c.status == RaidRegistrationStatus.validated,
            Second.c.status == RaidRegistrationStatus.validated,
        )
    )
    result = await db.execute(stmt)
    return result.scalar() or 0


async def create_participant_checkout(
    checkout: models_raid.RaidParticipantCheckout,
    db: AsyncSession,
) -> models_raid.RaidParticipantCheckout:
    db.add(checkout)
    await db.flush()
    return checkout


async def get_participant_checkout_by_checkout_id(
    checkout_id: str,
    db: AsyncSession,
) -> models_raid.RaidParticipantCheckout | None:
    checkout = await db.execute(
        select(models_raid.RaidParticipantCheckout).where(
            models_raid.RaidParticipantCheckout.checkout_id == checkout_id,
        ),
    )
    return checkout.scalars().first()


# --- Edition CRUDs ------------------------------------------------------


async def get_all_editions(
    db: AsyncSession,
) -> Sequence[models_raid.RaidEdition]:
    result = await db.execute(select(models_raid.RaidEdition))
    return result.scalars().all()


async def get_edition_by_id(
    edition_id: UUID,
    db: AsyncSession,
) -> models_raid.RaidEdition | None:
    result = await db.execute(
        select(models_raid.RaidEdition).where(
            models_raid.RaidEdition.id == edition_id,
        ),
    )
    return result.scalars().first()


async def get_active_edition(
    db: AsyncSession,
) -> models_raid.RaidEdition | None:
    result = await db.execute(
        select(models_raid.RaidEdition).where(
            models_raid.RaidEdition.active == True,  # noqa: E712
        ),
    )
    return result.scalars().first()


async def create_edition(
    edition: models_raid.RaidEdition,
    db: AsyncSession,
) -> models_raid.RaidEdition:
    db.add(edition)
    await db.flush()
    return edition


async def update_edition(
    edition_id: UUID,
    edit: schemas_raid.RaidEditionEdit,
    db: AsyncSession,
) -> None:
    values = edit.model_dump(exclude_none=True)
    if not values:
        return
    await db.execute(
        update(models_raid.RaidEdition)
        .where(models_raid.RaidEdition.id == edition_id)
        .values(**values),
    )
    await db.flush()


async def delete_edition(
    edition_id: UUID,
    db: AsyncSession,
) -> None:
    await db.execute(
        delete(models_raid.RaidEdition).where(
            models_raid.RaidEdition.id == edition_id,
        ),
    )
    await db.flush()


async def deactivate_all_editions(
    db: AsyncSession,
) -> None:
    await db.execute(
        update(models_raid.RaidEdition).values(active=False),
    )
    await db.flush()


# --- Volunteer CRUDs ---------------------------------------------------


async def create_volunteer(
    volunteer: models_raid.RaidVolunteer,
    db: AsyncSession,
) -> models_raid.RaidVolunteer:
    db.add(volunteer)
    await db.flush()
    return volunteer


async def get_volunteer_by_user_id(
    user_id: str,
    edition_id: UUID,
    db: AsyncSession,
) -> models_raid.RaidVolunteer | None:
    result = await db.execute(
        select(models_raid.RaidVolunteer).where(
            models_raid.RaidVolunteer.user_id == user_id,
            models_raid.RaidVolunteer.edition_id == edition_id,
        ),
    )
    return result.scalars().first()


async def get_all_volunteers_by_edition(
    edition_id: UUID,
    db: AsyncSession,
    validated: bool | None = None,
) -> Sequence[models_raid.RaidVolunteer]:
    stmt = select(models_raid.RaidVolunteer).where(
        models_raid.RaidVolunteer.edition_id == edition_id,
    )
    if validated is not None:
        stmt = stmt.where(models_raid.RaidVolunteer.validated == validated)
    result = await db.execute(stmt)
    return result.scalars().all()


async def update_volunteer(
    user_id: str,
    edition_id: UUID,
    values: dict,
    db: AsyncSession,
) -> None:
    if not values:
        return
    await db.execute(
        update(models_raid.RaidVolunteer)
        .where(
            models_raid.RaidVolunteer.user_id == user_id,
            models_raid.RaidVolunteer.edition_id == edition_id,
        )
        .values(**values),
    )
    await db.flush()


async def update_volunteer_validation(
    user_id: str,
    edition_id: UUID,
    validated: bool,
    db: AsyncSession,
) -> None:
    await db.execute(
        update(models_raid.RaidVolunteer)
        .where(
            models_raid.RaidVolunteer.user_id == user_id,
            models_raid.RaidVolunteer.edition_id == edition_id,
        )
        .values(validated=validated),
    )
    await db.flush()


async def update_volunteer_cancellation(
    user_id: str,
    edition_id: UUID,
    cancelled: bool,
    db: AsyncSession,
) -> None:
    await db.execute(
        update(models_raid.RaidVolunteer)
        .where(
            models_raid.RaidVolunteer.user_id == user_id,
            models_raid.RaidVolunteer.edition_id == edition_id,
        )
        .values(cancelled=cancelled),
    )
    await db.flush()


async def delete_volunteer(
    user_id: str,
    edition_id: UUID,
    db: AsyncSession,
) -> None:
    await db.execute(
        delete(models_raid.RaidVolunteer).where(
            models_raid.RaidVolunteer.user_id == user_id,
            models_raid.RaidVolunteer.edition_id == edition_id,
        ),
    )
    await db.flush()
