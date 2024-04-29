from sqlite3 import IntegrityError

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import models_raid
from app.schemas import schemas_raid


async def get_team_by_participant_id(
    participant_id: str,
    db: AsyncSession,
) -> models_raid.Team | None:
    team = await db.execute(
        select(models_raid.Team).where(
            models_raid.Team.captain_id == participant_id
            or models_raid.Team.second_id == participant_id
        )
    )
    return team.scalars().first()


async def get_all_teams(
    db: AsyncSession,
) -> list[models_raid.Team]:
    teams = await db.execute(select(models_raid.Team))
    return teams.scalars().all()


async def get_team_by_id(
    team_id: str,
    db: AsyncSession,
) -> models_raid.Team | None:
    team = await db.execute(
        select(models_raid.Team).where(models_raid.Team.id == team_id)
    )
    return team.scalars().first()


async def create_team(
    team: schemas_raid.Team,
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
    team: models_raid.TeamUpdate,
    db: AsyncSession,
) -> None:
    await db.execute(
        update(schemas_raid.Team)
        .where(schemas_raid.Team.id == team_id)
        .values(**team.dict(exclude_none=True))
    )
    await db.commit()


async def delete_team(
    team_id: str,
    db: AsyncSession,
) -> None:
    await db.execute(delete(models_raid.Team).where(models_raid.Team.id == team_id))
    await db.commit()


async def get_document_by_id(
    document_id: str,
    db: AsyncSession,
) -> models_raid.Document | None:
    document = await db.execute(
        select(models_raid.Document).where(models_raid.Document.id == document_id)
    )
    return document.scalars().first()


async def upload_document(
    document: schemas_raid.Document,
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
    participant = await get_participant_by_id(participant_id, db)
    if participant:
        await db.execute(
            update(models_raid.Participant)
            .where(models_raid.Participant.id == participant_id)
            .values(
                validation_progress=(models_raid.Participant.validation_progress + 1)
            )
        )
    await db.commit()


async def update_document(
    document_id: str,
    document: schemas_raid.DocumentUpdate,
    db: AsyncSession,
) -> None:
    await db.execute(
        update(models_raid.Document)
        .where(models_raid.Document.id == document_id)
        .values(**document.dict(exclude_none=True))
    )
    participant = await get_participant_by_id(document.participant_id, db)
    if participant:
        await db.execute(
            update(models_raid.Participant)
            .where(models_raid.Participant.id == document.participant_id)
            .values(
                validation_progress=(models_raid.Participant.validation_progress - 1)
            )
        )
    await db.commit()


async def delete_document(
    document_id: str,
    db: AsyncSession,
) -> None:
    await db.execute(
        delete(models_raid.Document).where(models_raid.Document.id == document_id)
    )
    participant = await db.execute(
        select(models_raid.Participant).where(
            models_raid.Participant.document_id == document_id
        )
    )
    participant = await get_participant_by_id(participant.id, db)
    if participant:
        await db.execute(
            update(models_raid.Participant)
            .where(models_raid.Participant.id == participant.id)
            .values(
                validation_progress=(models_raid.Participant.validation_progress - 1)
            )
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
        select(models_raid.Participant).where(
            models_raid.Participant.id == participant_id
        )
    )
    return participant.scalars().first()
