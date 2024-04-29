from datetime import UTC, datetime
from sqlalchemy.exc import IntegrityError
from typing import Sequence

from sqlalchemy import delete, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.raid import models_raid, schemas_raid


async def create_participant(
    participant: models_raid.Participant,
    db: AsyncSession,
) -> models_raid.Participant:
    db.add(participant)
    try:
        await db.commit()
        return participant
    except IntegrityError:
        await db.rollback()
        raise ValueError("An error occurred while creating the participant.")


async def update_participant(
    participant_id: str,
    participant: schemas_raid.ParticipantUpdate,
    db: AsyncSession,
) -> None:
    await db.execute(
        update(models_raid.Participant)
        .where(models_raid.Participant.id == participant_id)
        .values(**participant.model_dump(exclude_none=True))
    )
    await db.commit()


async def is_user_a_participant(
    user_id: str,
    db: AsyncSession,
) -> bool:
    participant = await db.execute(
        select(models_raid.Participant).where(models_raid.Participant.id == user_id)
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
            )
        )
        .options(
            selectinload("*"),
        )
    )
    return team.scalars().first()


async def get_all_teams(
    db: AsyncSession,
) -> Sequence[models_raid.Team]:
    teams = await db.execute(
        select(models_raid.Team).options(
            selectinload("*"),
        )
    )
    return teams.scalars().all()


async def get_team_by_id(
    team_id: str,
    db: AsyncSession,
) -> models_raid.Team | None:
    team = await db.execute(
        select(models_raid.Team)
        .where(models_raid.Team.id == team_id)
        .options(
            selectinload("*"),
        )
    )
    return team.scalars().first()


async def create_team(
    team: models_raid.Team,
    db: AsyncSession,
) -> models_raid.Team:
    db.add(team)
    try:
        await db.commit()
        return team
    except IntegrityError:
        await db.rollback()
        raise ValueError("An error occurred while creating the team.")


async def update_team(
    team_id: str,
    team: schemas_raid.TeamUpdate,
    db: AsyncSession,
) -> None:
    await db.execute(
        update(models_raid.Team)
        .where(models_raid.Team.id == team_id)
        .values(**team.model_dump(exclude_none=True))
    )
    await db.commit()


async def delete_team(
    team_id: str,
    db: AsyncSession,
) -> None:
    await db.execute(delete(models_raid.Team).where(models_raid.Team.id == team_id))
    await db.commit()


async def delete_all_teams(
    db: AsyncSession,
) -> None:
    await db.execute(delete(models_raid.Team))
    await db.commit()


async def add_security_file(
    security_file: schemas_raid.SecurityFile,
    db: AsyncSession,
) -> models_raid.SecurityFile:
    db.add(security_file)
    try:
        await db.commit()
        return security_file
    except IntegrityError:
        await db.rollback()
        raise ValueError("An error occurred while creating the participant.")


async def update_security_file(
    security_file: schemas_raid.SecurityFile,
    db: AsyncSession,
) -> None:
    await db.execute(
        update(models_raid.SecurityFile)
        .where(models_raid.SecurityFile.id == security_file.id)
        .values(**security_file.model_dump(exclude_none=True))
    )
    await db.commit()


async def assign_security_file(
    participant_id: str,
    security_file_id: str,
    db: AsyncSession,
) -> None:
    await db.execute(
        update(models_raid.Participant)
        .where(models_raid.Participant.id == participant_id)
        .values(security_file_id=security_file_id)
    )
    await db.commit()


async def create_document(
    document: models_raid.Document,
    db: AsyncSession,
) -> models_raid.Document:
    db.add(document)
    try:
        await db.commit()
        return document
    except IntegrityError:
        await db.rollback()
        raise ValueError("An error occurred while creating the document.")


async def assign_document(
    participant_id: str,
    document_id: str,
    document_key: str,
    db: AsyncSession,
) -> None:
    await db.execute(
        update(models_raid.Participant)
        .where(models_raid.Participant.id == participant_id)
        .values({document_key: document_id})
    )
    await db.commit()


async def get_document_by_id(
    document_id: str,
    db: AsyncSession,
) -> models_raid.Document | None:
    document = await db.execute(
        select(models_raid.Document).where(models_raid.Document.id == document_id)
    )
    return document.scalars().first()


async def get_user_by_document_id(
    document_id: str, db: AsyncSession
) -> models_raid.Participant | None:
    document = await db.execute(
        select(models_raid.Participant).where(
            or_(
                models_raid.Participant.id_card_id == document_id,
                models_raid.Participant.medical_certificate_id == document_id,
                models_raid.Participant.student_card_id == document_id,
                models_raid.Participant.raid_rules_id == document_id,
            ),
        )
    )
    return document.scalars().first()


async def upload_document(
    document: models_raid.Document,
    db: AsyncSession,
) -> models_raid.Document:
    db.add(document)
    try:
        await db.commit()
        return document
    except IntegrityError:
        await db.rollback()
        raise ValueError("An error occurred while uploading the document.")


async def validate_document(
    document_id: str,
    participant_id: str,
    db: AsyncSession,
) -> None:
    await db.execute(
        update(models_raid.Document)
        .where(models_raid.Document.id == document_id)
        .values(validated=True)
    )

    await db.commit()


async def update_document(
    document_id: str,
    document: schemas_raid.DocumentBase,
    db: AsyncSession,
) -> None:
    await db.execute(
        update(models_raid.Document)
        .where(models_raid.Document.id == document_id)
        .values(**document.model_dump(exclude_none=True))
    )
    await db.commit()


async def mark_document_as_newly_updated(
    document_id: str,
    db: AsyncSession,
):
    await db.execute(
        update(models_raid.Document)
        .where(models_raid.Document.id == document_id)
        .values(uploaded_at=datetime.now(tz=UTC).date(), validated=False)
    )

    await db.commit()


async def confirm_payment(
    participant_id: str,
    db: AsyncSession,
) -> None:
    await db.execute(
        update(models_raid.Participant)
        .where(models_raid.Participant.id == participant_id)
        .values(payment=True)
    )
    await db.commit()


async def validate_attestation_on_honour(
    participant_id: str,
    db: AsyncSession,
) -> None:
    await db.execute(
        update(models_raid.Participant)
        .where(models_raid.Participant.id == participant_id)
        .values(attestation_on_honour=True)
    )
    await db.commit()


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
            models_raid.SecurityFile.id == security_id
        )
    )
    return security_file.scalars().first()


async def create_invite_token(
    invite: models_raid.InviteToken,
    db: AsyncSession,
) -> models_raid.InviteToken:
    db.add(invite)
    try:
        await db.commit()
        return invite
    except IntegrityError:
        await db.rollback()
        raise ValueError("An error occurred while creating the invite token.")


async def get_invite_token_by_team_id(
    team_id: str,
    db: AsyncSession,
) -> models_raid.InviteToken | None:
    invite = await db.execute(
        select(models_raid.InviteToken).where(
            models_raid.InviteToken.team_id == team_id
        )
    )
    return invite.scalars().first()


async def get_invite_token_by_token(
    token: str,
    db: AsyncSession,
) -> models_raid.InviteToken | None:
    invite = await db.execute(
        select(models_raid.InviteToken).where(models_raid.InviteToken.token == token)
    )
    return invite.scalars().first()


async def update_team_second_id(
    team_id: str,
    second_id: str,
    db: AsyncSession,
) -> None:
    await db.execute(
        update(models_raid.Team)
        .where(models_raid.Team.id == team_id)
        .values(second_id=second_id)
    )
    await db.commit()


async def delete_invite_token(
    token_id: str,
    db: AsyncSession,
) -> None:
    await db.execute(
        delete(models_raid.InviteToken).where(
            models_raid.InviteToken.id == token_id
        )
    )
    await db.commit()
