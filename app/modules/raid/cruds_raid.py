from collections import defaultdict
from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import delete, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.raid import models_raid, schemas_raid
from app.modules.raid.raid_type import Difficulty, DocumentValidation


async def create_participant(
    participant: models_raid.RaidParticipant,
    db: AsyncSession,
) -> models_raid.RaidParticipant:
    db.add(participant)
    await db.flush()
    return participant


async def get_all_participants(
    db: AsyncSession,
) -> Sequence[models_raid.RaidParticipant]:
    participants = await db.execute(
        select(models_raid.RaidParticipant).options(
            # Since there is nested classes in the RaidParticipant model, we need to load all the related data
            selectinload("*"),
        ),
    )
    return participants.scalars().all()


async def update_participant(
    participant_id: str,
    participant: schemas_raid.RaidParticipantUpdate,
    is_minor: bool | None,
    db: AsyncSession,
) -> None:
    query = (
        update(models_raid.RaidParticipant)
        .where(models_raid.RaidParticipant.id == participant_id)
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
        update(models_raid.RaidParticipant)
        .where(models_raid.RaidParticipant.id == participant_id)
        .values(is_minor=is_minor),
    )
    await db.flush()


async def is_user_a_participant(
    user_id: str,
    db: AsyncSession,
) -> bool:
    participant = await db.execute(
        select(models_raid.RaidParticipant).where(
            models_raid.RaidParticipant.id == user_id,
        ),
    )
    return bool(participant.scalars().first())


async def get_team_by_participant_id(
    participant_id: str,
    db: AsyncSession,
) -> models_raid.RaidTeam | None:
    team = await db.execute(
        select(models_raid.RaidTeam)
        .where(
            or_(
                models_raid.RaidTeam.captain_id == participant_id,
                models_raid.RaidTeam.second_id == participant_id,
            ),
        )
        .options(
            # Since there is nested classes in the RaidTeam model, we need to load all the related data
            selectinload("*"),
        ),
    )
    return team.scalars().first()


async def get_all_teams(
    db: AsyncSession,
) -> Sequence[models_raid.RaidTeam]:
    teams = await db.execute(
        select(models_raid.RaidTeam).options(
            # Since there is nested classes in the RaidTeam model, we need to load all the related data
            selectinload("*"),
        ),
    )
    return teams.scalars().all()


async def get_all_validated_teams(
    db: AsyncSession,
) -> Sequence[models_raid.RaidTeam]:
    teams = await db.execute(
        select(models_raid.RaidTeam).options(
            # Since there is nested classes in the RaidTeam model, we need to load all the related data
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
) -> models_raid.RaidTeam | None:
    team = await db.execute(
        select(models_raid.RaidTeam)
        .where(models_raid.RaidTeam.id == team_id)
        .options(
            # Since there is nested classes in the RaidTeam model, we need to load all the related data
            selectinload("*"),
        ),
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
    await db.execute(
        update(models_raid.RaidTeam)
        .where(models_raid.RaidTeam.id == team_id)
        .values(**team.model_dump(exclude_none=True)),
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
    participant_id: str,
    db: AsyncSession,
) -> None:
    await db.execute(
        delete(models_raid.RaidParticipant).where(
            models_raid.RaidParticipant.id == participant_id,
        ),
    )
    await db.flush()


async def delete_all_participant(
    db: AsyncSession,
) -> None:
    await db.execute(delete(models_raid.RaidParticipant))
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
    await db.execute(
        delete(models_raid.RaidTeam).where(models_raid.RaidTeam.id == team_id),
    )
    await db.flush()


async def delete_all_teams(
    db: AsyncSession,
) -> None:
    await db.execute(delete(models_raid.RaidTeam))
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
        update(models_raid.RaidParticipant)
        .where(models_raid.RaidParticipant.id == participant_id)
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
    document_id: str | None,
    document_key: str,
    db: AsyncSession,
) -> None:
    await db.execute(
        update(models_raid.RaidParticipant)
        .where(models_raid.RaidParticipant.id == participant_id)
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
        update(models_raid.RaidParticipant)
        .where(models_raid.RaidParticipant.id == participant_id)
        .values(payment=True),
    )
    await db.flush()


async def confirm_t_shirt_payment(
    participant_id: str,
    db: AsyncSession,
) -> None:
    await db.execute(
        update(models_raid.RaidParticipant)
        .where(models_raid.RaidParticipant.id == participant_id)
        .values(t_shirt_payment=True),
    )
    await db.flush()


async def validate_attestation_on_honour(
    participant_id: str,
    db: AsyncSession,
) -> None:
    await db.execute(
        update(models_raid.RaidParticipant)
        .where(models_raid.RaidParticipant.id == participant_id)
        .values(attestation_on_honour=True),
    )
    await db.flush()


async def get_participant_by_id(
    participant_id: str,
    db: AsyncSession,
) -> models_raid.RaidParticipant | None:
    participant = await db.execute(
        select(models_raid.RaidParticipant)
        .where(models_raid.RaidParticipant.id == participant_id)
        .options(
            selectinload("*"),
        ),
    )
    return participant.scalars().first()


async def get_number_of_teams(
    db: AsyncSession,
) -> int:
    result = await db.execute(select(models_raid.RaidTeam))
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
) -> models_raid.RaidTeam | None:
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
        update(models_raid.RaidTeam)
        .where(models_raid.RaidTeam.id == team_id)
        .values(file_id=file_id),
    )
    await db.flush()


async def get_number_of_team_by_difficulty(
    difficulty: Difficulty,
    db: AsyncSession,
) -> int:
    result = await db.execute(
        select(models_raid.RaidTeam).where(
            models_raid.RaidTeam.difficulty == difficulty,
        ),
    )
    teams_found = result.scalars().all()
    # We can not use a where clause because the validation_progress is a Python property
    # and is not usable in a SQL query
    team_numbers = [
        team.number if team.number is not None and team.number >= 0 else 0
        for team in filter(
            lambda team: team.validation_progress == 100
            and team.number is not None
            and team.number >= 0,
            teams_found,
        )
    ]
    return max(team_numbers) if team_numbers else 0


async def create_participant_checkout(
    checkout: models_raid.RaidParticipantCheckout,
    db: AsyncSession,
) -> models_raid.RaidParticipantCheckout:
    db.add(checkout)
    await db.flush()
    return checkout


async def get_participant_checkout_by_checkout_id(
    # TODO: use UUID
    checkout_id: str,
    db: AsyncSession,
) -> models_raid.RaidParticipantCheckout | None:
    checkout = await db.execute(
        select(models_raid.RaidParticipantCheckout).where(
            models_raid.RaidParticipantCheckout.checkout_id == checkout_id,
        ),
    )
    return checkout.scalars().first()


#################################### CRUDS FOR CHRONO RAID ####################################


async def get_temps(
    db: AsyncSession,
) -> Sequence[models_raid.Temps]:
    temps = await db.execute(select(models_raid.Temps))
    return temps.scalars().all()


async def get_active_temps_grouped_by_dossard(
    parcours: str,
    db: AsyncSession,
) -> dict[int, list[models_raid.Temps]]:
    result = await db.execute(
        select(models_raid.Temps)
        .where(models_raid.Temps.status and models_raid.Temps.parcours == parcours)
        .order_by(models_raid.Temps.dossard, models_raid.Temps.date),
    )
    temps_list = result.scalars().all()
    grouped_temps = defaultdict(list)
    for temps in temps_list:
        grouped_temps[temps.dossard].append(temps)
    return dict(grouped_temps)


async def get_temps_by_date(
    date: str,
    db: AsyncSession,
) -> Sequence[models_raid.Temps]:
    temps = await db.execute(
        select(models_raid.Temps).where(
            models_raid.Temps.last_modification_date >= date,
        ),
    )
    return temps.scalars().all()


async def get_temps_by_id(
    temps_id: str,
    db: AsyncSession,
) -> models_raid.Temps | None:
    temps = await db.execute(
        select(models_raid.Temps).where(models_raid.Temps.id == temps_id),
    )
    return temps.scalars().first()


async def add_temps(
    temps: schemas_raid.Temps,
    db: AsyncSession,
) -> models_raid.Temps:
    temps_db = models_raid.Temps(**temps.model_dump())
    db.add(temps_db)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise
    else:
        return temps_db


async def update_temps(
    temps: schemas_raid.Temps,
    db: AsyncSession,
) -> schemas_raid.Temps:
    await db.execute(
        update(models_raid.Temps)
        .where(models_raid.Temps.id == temps.id)
        .values(**temps.model_dump(exclude_none=True)),
    )
    await db.commit()
    return temps


async def delete_all_times(
    db: AsyncSession,
):
    await db.execute(delete(models_raid.Temps))
    await db.commit()


async def get_remarks(
    db: AsyncSession,
) -> Sequence[models_raid.Remark]:
    remarks = await db.execute(select(models_raid.Remark))
    return remarks.scalars().all()


async def add_remarks(
    list_remarks: list[schemas_raid.Remark],
    db: AsyncSession,
):
    for remark in list_remarks:
        remark_db = models_raid.Remark(**remark.model_dump())
        db.add(remark_db)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise


async def delete_all_remarks(
    db: AsyncSession,
):
    await db.execute(delete(models_raid.Remark))
    await db.commit()
