from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import delete, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.raid import models_raid, schemas_raid
from app.modules.raid.raid_type import Difficulty, DocumentValidation


async def create_participant(
    participant: models_raid.Participant,
    db: AsyncSession,
) -> models_raid.Participant:
    db.add(participant)
    await db.flush()
    return participant


async def get_all_participants(
    db: AsyncSession,
) -> Sequence[models_raid.Participant]:
    participants = await db.execute(
        select(models_raid.Participant).options(
            # Since there is nested classes in the Participant model, we need to load all the related data
            selectinload("*"),
        ),
    )
    return participants.scalars().all()


async def update_participant(
    participant_id: str,
    participant: schemas_raid.ParticipantUpdate,
    is_minor: bool | None,
    db: AsyncSession,
) -> None:
    query = (
        update(models_raid.Participant)
        .where(models_raid.Participant.id == participant_id)
        .values(**participant.model_dump(exclude_none=True))
    )

    if is_minor:
        query = query.values(is_minor=is_minor)
    await db.execute(query)
    await db.flush()


async def update_participant_minority(
    participant_id: str,
    is_minor: bool,
    db: AsyncSession,
) -> None:
    await db.execute(
        update(models_raid.Participant)
        .where(models_raid.Participant.id == participant_id)
        .values(is_minor=is_minor),
    )
    await db.flush()


async def is_user_a_participant(
    user_id: str,
    db: AsyncSession,
) -> bool:
    participant = await db.execute(
        select(models_raid.Participant).where(models_raid.Participant.id == user_id),
    )
    return bool(participant.scalars().first())


async def get_team_by_participant_id(
    participant_id: str,
    db: AsyncSession,
) -> models_raid.Team | None:
    team = await db.execute(
        select(models_raid.Team)
        .where(
            or_(
                models_raid.Team.captain_id == participant_id,
                models_raid.Team.second_id == participant_id,
            ),
        )
        .options(
            # Since there is nested classes in the Team model, we need to load all the related data
            selectinload("*"),
        ),
    )
    return team.scalars().first()


async def get_all_teams(
    db: AsyncSession,
) -> Sequence[models_raid.Team]:
    teams = await db.execute(
        select(models_raid.Team).options(
            # Since there is nested classes in the Team model, we need to load all the related data
            selectinload("*"),
        ),
    )
    return teams.scalars().all()


async def get_all_validated_teams(
    db: AsyncSession,
) -> Sequence[models_raid.Team]:
    teams = await db.execute(
        select(models_raid.Team).options(
            # Since there is nested classes in the Team model, we need to load all the related data
            selectinload("*"),
        ),
    )
    teams_found = teams.scalars().all()
    # We can not use a where clause because the validation_progress is a Python property
    # and is not usable in a SQL query
    return list(filter(lambda team: team.validation_progress == 100, teams_found))


async def get_team_by_id(
    team_id: str,
    db: AsyncSession,
) -> models_raid.Team | None:
    team = await db.execute(
        select(models_raid.Team)
        .where(models_raid.Team.id == team_id)
        .options(
            # Since there is nested classes in the Team model, we need to load all the related data
            selectinload("*"),
        ),
    )
    return team.scalars().first()


async def create_team(
    team: models_raid.Team,
    db: AsyncSession,
) -> None:
    db.add(team)
    await db.flush()


async def update_team(
    team_id: str,
    team: schemas_raid.TeamUpdate,
    db: AsyncSession,
) -> None:
    await db.execute(
        update(models_raid.Team)
        .where(models_raid.Team.id == team_id)
        .values(**team.model_dump(exclude_none=True)),
    )
    await db.flush()


async def update_team_captain_id(
    team_id: str,
    captain_id: str,
    db: AsyncSession,
) -> None:
    await db.execute(
        update(models_raid.Team)
        .where(models_raid.Team.id == team_id)
        .values(captain_id=captain_id),
    )
    await db.flush()


async def update_team_second_id(
    team_id: str,
    second_id: str | None,
    db: AsyncSession,
) -> None:
    await db.execute(
        update(models_raid.Team)
        .where(models_raid.Team.id == team_id)
        .values(second_id=second_id),
    )
    await db.flush()


async def delete_participant(
    participant_id: str,
    db: AsyncSession,
) -> None:
    await db.execute(
        delete(models_raid.Participant).where(
            models_raid.Participant.id == participant_id,
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
    db: AsyncSession,
) -> None:
    await db.execute(delete(models_raid.InviteToken))
    await db.flush()


async def delete_team(
    team_id: str,
    db: AsyncSession,
) -> None:
    await db.execute(delete(models_raid.Team).where(models_raid.Team.id == team_id))
    await db.flush()


async def delete_all_teams(
    db: AsyncSession,
) -> None:
    await db.execute(delete(models_raid.Team))
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
    participant_id: str,
    security_file_id: str,
    db: AsyncSession,
) -> None:
    await db.execute(
        update(models_raid.Participant)
        .where(models_raid.Participant.id == participant_id)
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
    participant_id: str,
    document_id: str,
    document_key: str,
    db: AsyncSession,
) -> None:
    await db.execute(
        update(models_raid.Participant)
        .where(models_raid.Participant.id == participant_id)
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
) -> models_raid.Participant | None:
    document = await db.execute(
        select(models_raid.Participant).where(
            or_(
                models_raid.Participant.id_card_id == document_id,
                models_raid.Participant.medical_certificate_id == document_id,
                models_raid.Participant.student_card_id == document_id,
                models_raid.Participant.raid_rules_id == document_id,
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
    participant_id: str,
    db: AsyncSession,
) -> None:
    await db.execute(
        update(models_raid.Participant)
        .where(models_raid.Participant.id == participant_id)
        .values(payment=True),
    )
    await db.flush()


async def confirm_t_shirt_payment(
    participant_id: str,
    db: AsyncSession,
) -> None:
    await db.execute(
        update(models_raid.Participant)
        .where(models_raid.Participant.id == participant_id)
        .values(t_shirt_payment=True),
    )
    await db.flush()


async def validate_attestation_on_honour(
    participant_id: str,
    db: AsyncSession,
) -> None:
    await db.execute(
        update(models_raid.Participant)
        .where(models_raid.Participant.id == participant_id)
        .values(attestation_on_honour=True),
    )
    await db.flush()


async def get_participant_by_id(
    participant_id: str,
    db: AsyncSession,
) -> models_raid.Participant | None:
    participant = await db.execute(
        select(models_raid.Participant)
        .where(models_raid.Participant.id == participant_id)
        .options(
            selectinload("*"),
        ),
    )
    return participant.scalars().first()


async def get_number_of_teams(
    db: AsyncSession,
) -> int:
    result = await db.execute(select(models_raid.Team))
    return len(result.scalars().all())


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


async def are_user_in_the_same_team(
    participant_id_1: str,
    participant_id_2: str,
    db: AsyncSession,
) -> bool:
    return (
        await get_team_if_users_in_the_same_team(
            participant_id_1=participant_id_1,
            participant_id_2=participant_id_2,
            db=db,
        )
        is not None
    )


async def get_team_if_users_in_the_same_team(
    participant_id_1: str,
    participant_id_2: str,
    db: AsyncSession,
) -> models_raid.Team | None:
    team_1 = await get_team_by_participant_id(participant_id_1, db)
    team_2 = await get_team_by_participant_id(participant_id_2, db)
    if team_1 is None or team_2 is None:
        return None
    if team_1.id != team_2.id:
        return None
    return team_1


async def update_team_file_id(
    team_id: str,
    file_id: str,
    db: AsyncSession,
) -> None:
    await db.execute(
        update(models_raid.Team)
        .where(models_raid.Team.id == team_id)
        .values(file_id=file_id),
    )
    await db.flush()


async def get_number_of_team_by_difficulty(
    difficulty: Difficulty,
    db: AsyncSession,
) -> int:
    result = await db.execute(
        select(models_raid.Team).where(models_raid.Team.difficulty == difficulty),
    )
    teams_found = result.scalars().all()
    # We can not use a where clause because the validation_progress is a Python property
    # and is not usable in a SQL query
    return len(
        list(
            filter(
                lambda team: team.validation_progress == 100
                and team.number is not None
                and team.number >= 0,
                teams_found,
            ),
        ),
    )


async def create_participant_checkout(
    checkout: models_raid.ParticipantCheckout,
    db: AsyncSession,
) -> models_raid.ParticipantCheckout:
    db.add(checkout)
    await db.flush()
    return checkout


async def get_participant_checkout_by_checkout_id(
    # TODO: use UUID
    checkout_id: str,
    db: AsyncSession,
) -> models_raid.ParticipantCheckout | None:
    checkout = await db.execute(
        select(models_raid.ParticipantCheckout).where(
            models_raid.ParticipantCheckout.checkout_id == checkout_id,
        ),
    )
    return checkout.scalars().first()
