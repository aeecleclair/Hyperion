import logging
import uuid
from collections.abc import Sequence
from datetime import UTC, date, datetime
from pathlib import Path

import aiofiles
from fastapi import Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import models_core, standard_responses
from app.core.config import Settings
from app.core.groups.groups_type import GroupType
from app.core.module import Module
from app.core.payment.payment_tool import PaymentTool
from app.dependencies import (
    get_db,
    get_request_id,
    get_settings,
    is_user,
    is_user_a_member_of,
)
from app.modules.raid import cruds_raid, models_raid, schemas_raid
from app.modules.raid.raid_type import DocumentType, DocumentValidation
from app.modules.raid.utils.drive.drive_file_manager import DriveFileManager
from app.modules.raid.utils.pdf.pdf_writer import HTMLPDFWriter, PDFWriter
from app.types.content_type import ContentType
from app.utils.tools import (
    get_core_data,
    get_file_from_data,
    get_random_string,
    is_user_member_of_an_allowed_group,
    save_file_as_data,
    set_core_data,
)

module = Module(
    root="raid",
    tag="Raid",
    default_allowed_groups_ids=[GroupType.student, GroupType.staff],
)

hyperion_error_logger = logging.getLogger("hyperion.error")

drive_file_manager = DriveFileManager()


async def write_teams_csv(teams: Sequence[models_raid.Team], db: AsyncSession) -> None:
    file_name = "Équipes - " + datetime.now(UTC).strftime("%Y-%m-%d_%H_%M_%S") + ".csv"
    file_path = "data/raid/" + file_name
    data: list[list[str]] = [["Team name", "Captain", "Second", "Difficulty", "Number"]]
    for team in teams:
        data.append(
            [
                team.name.replace(",", " "),
                f"{team.captain.firstname} {team.captain.name}".replace(",", " "),
                f"{team.second.firstname} {team.second.name}".replace(",", " ")
                if team.second
                else "",
                team.difficulty,
                str(team.number or ""),
            ],
        )
    async with aiofiles.open(
        file_path,
        mode="w",
        newline="",
        encoding="utf-8",
    ) as file:
        for line in data:
            await file.write(",".join(line) + "\n")

    await drive_file_manager.upload_raid_file(file_path, file_name, db)
    Path(file_path).unlink()


async def set_team_number(team: models_raid.Team, db: AsyncSession) -> None:
    new_team_number = await cruds_raid.get_number_of_team_by_difficulty(
        team.difficulty,
        db,
    )
    updated_team: schemas_raid.TeamUpdate = schemas_raid.TeamUpdate(
        number=new_team_number,
    )
    await cruds_raid.update_team(team.id, updated_team, db)


async def save_team_info(team: models_raid.Team, db: AsyncSession) -> None:
    try:
        pdf_writer = PDFWriter()
        file_path = pdf_writer.write_team(team)
        file_name = file_path.split("/")[-1]
        if team.file_id:
            try:
                file_id = drive_file_manager.replace_file(file_path, team.file_id)
            except Exception:
                file_id = await drive_file_manager.upload_team_file(
                    file_path,
                    file_name,
                    db,
                )
        else:
            file_id = await drive_file_manager.upload_team_file(
                file_path,
                file_name,
                db,
            )
        await cruds_raid.update_team_file_id(team.id, file_id, db)
        pdf_writer.clear_pdf()
    except Exception as error:
        hyperion_error_logger.error(f"Error while creating pdf, {error}")
        return None


async def post_update_actions(team: models_raid.Team | None, db: AsyncSession) -> None:
    if team:
        if team.validation_progress == 100:
            await set_team_number(team, db)
            all_teams = await cruds_raid.get_all_validated_teams(db)
            if all_teams:
                await write_teams_csv(all_teams, db)
        await save_team_info(team, db)


async def save_security_file(
    participant: models_raid.Participant,
    team_number: int | None,
    db: AsyncSession,
) -> None:
    try:
        pdf_writer = HTMLPDFWriter()
        file_path = pdf_writer.write_participant_security_file(participant, team_number)
        file_name = f"{str(team_number) + '_' if team_number else ''}{participant.firstname}_{participant.name}_fiche_sécurité.pdf"
        if participant.security_file and participant.security_file.file_id:
            file_id = drive_file_manager.replace_file(
                file_path,
                participant.security_file.file_id,
            )
        else:
            file_id = await drive_file_manager.upload_participant_file(
                file_path,
                file_name,
                db,
            )
        if not participant.security_file:
            security_file = models_raid.SecurityFile(
                id=str(uuid.uuid4()),
                file_id=file_id,
            )
            await cruds_raid.add_security_file(security_file, db)
        else:
            await cruds_raid.update_security_file_id(
                participant.security_file.id,
                file_id,
                db,
            )
        Path(file_path).unlink()
    except Exception as error:
        hyperion_error_logger.error(f"Error while creating pdf, {error.__dict__}")
        return None


@module.router.get(
    "/raid/participants/{participant_id}",
    response_model=schemas_raid.Participant,
    status_code=200,
)
async def get_participant_by_id(
    participant_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user),
):
    """
    Get a participant by id
    """
    if participant_id != user.id and not is_user_member_of_an_allowed_group(
        user,
        [GroupType.raid_admin],
    ):
        raise HTTPException(
            status_code=403,
            detail="You can not get data of another user",
        )

    participant = await cruds_raid.get_participant_by_id(participant_id, db)
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found.")

    return participant


@module.router.post(
    "/raid/participants",
    response_model=schemas_raid.Participant,
    status_code=201,
)
async def create_participant(
    participant: schemas_raid.ParticipantBase,
    user: models_core.CoreUser = Depends(is_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a participant
    """
    # If the user is already a participant, return an error
    if await cruds_raid.is_user_a_participant(user.id, db):
        raise HTTPException(status_code=403, detail="You are already a participant.")

    raid_information = await get_core_data(schemas_raid.RaidInformation, db)
    raid_start_date = raid_information.raid_start_date or date(
        year=datetime.now(UTC).year + 1,
        month=1,
        day=1,
    )

    is_minor = (
        date(
            participant.birthday.year + 18,
            participant.birthday.month,
            participant.birthday.day,
        )
        > raid_start_date
    )

    db_participant = models_raid.Participant(
        **participant.__dict__,
        id=user.id,
        is_minor=is_minor,
    )
    return await cruds_raid.create_participant(db_participant, db)


@module.router.patch(
    "/raid/participants/{participant_id}",
    status_code=204,
)
async def update_participant(
    participant_id: str,
    participant: schemas_raid.ParticipantUpdate,
    user: models_core.CoreUser = Depends(is_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update a participant
    """
    # If the user is not a participant, return an error
    if not await cruds_raid.is_user_a_participant(participant_id, db):
        raise HTTPException(status_code=403, detail="You are not a participant.")

    # If the user is not the participant, return an error
    if not await cruds_raid.are_user_in_the_same_team(user.id, participant_id, db):
        raise HTTPException(status_code=403, detail="You are not the participant.")

    raid_information = await get_core_data(schemas_raid.RaidInformation, db)
    raid_start_date = raid_information.raid_start_date or date(
        year=datetime.now(UTC).year + 1,
        month=1,
        day=1,
    )

    # We only want to change the is_minor value if the birthday is changed
    is_minor = None
    if participant.birthday:
        is_minor = (
            date(
                participant.birthday.year + 18,
                participant.birthday.month,
                participant.birthday.day,
            )
            > raid_start_date
        )

    saved_participant = await cruds_raid.get_participant_by_id(participant_id, db)
    participant_dict = participant.model_dump(exclude_none=True)
    # We remove the value to control it the way we want
    if participant_dict.get("t_shirt_size"):
        del participant_dict["t_shirt_size"]
    # If the t_shirt_payment is not set, we can change the t_shirt_size
    if not saved_participant.t_shirt_payment:
        participant_dict["t_shirt_size"] = (
            participant.t_shirt_size.value if participant.t_shirt_size else None
        )
    # If the t_shirt_payment is set, we can only change the t_shirt_size, but can not make it null
    elif participant.t_shirt_size:
        participant_dict["t_shirt_size"] = participant.t_shirt_size.value
    await cruds_raid.update_participant(participant_id, participant_dict, is_minor, db)
    team = await cruds_raid.get_team_by_participant_id(participant_id, db)
    await post_update_actions(team, db)


@module.router.post(
    "/raid/teams",
    response_model=schemas_raid.TeamBase,
    status_code=201,
)
async def create_team(
    team: schemas_raid.TeamBase,
    user: models_core.CoreUser = Depends(is_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a team
    """
    # If the user is not a participant, return an error
    if not await cruds_raid.is_user_a_participant(user.id, db):
        raise HTTPException(status_code=403, detail="You are not a participant.")

    # If the user already has a team, return an error
    if await cruds_raid.get_team_by_participant_id(user.id, db):
        raise HTTPException(status_code=403, detail="You already have a team.")

    db_team = models_raid.Team(
        id=str(uuid.uuid4()),
        name=team.name,
        number=None,
        captain_id=user.id,
        second_id=None,
    )
    created_team = await cruds_raid.create_team(db_team, db)
    await post_update_actions(created_team, db)
    return created_team


@module.router.get(
    "/raid/participants/{participant_id}/team",
    response_model=schemas_raid.Team,
    status_code=200,
)
async def get_team_by_participant_id(
    participant_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user),
):
    """
    Get a team by participant id
    """
    if user.id != participant_id:
        raise HTTPException(status_code=403, detail="You are not the participant.")

    # If the user is not a participant, return an error
    if not await cruds_raid.is_user_a_participant(participant_id, db):
        raise HTTPException(status_code=403, detail="You are not a participant.")

    participant_team = await cruds_raid.get_team_by_participant_id(participant_id, db)
    # If the user does not have a team, return an error
    if not participant_team:
        raise HTTPException(status_code=404, detail="You do not have a team.")
    return participant_team


@module.router.get(
    "/raid/teams",
    response_model=list[schemas_raid.TeamPreview],
    status_code=200,
)
async def get_all_teams(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.raid_admin)),
):
    """
    Get all teams
    """
    return await cruds_raid.get_all_teams(db)


@module.router.get(
    "/raid/teams/{team_id}",
    response_model=schemas_raid.Team,
    status_code=200,
)
async def get_team_by_id(
    team_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.raid_admin)),
):
    """
    Get a team by id
    """
    return await cruds_raid.get_team_by_id(team_id, db)


@module.router.patch(
    "/raid/teams/{team_id}",
    status_code=204,
)
async def update_team(
    team_id: str,
    team: schemas_raid.TeamUpdate,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user),
):
    """
    Update a team
    """
    existing_team = await cruds_raid.get_team_by_participant_id(user.id, db)
    if existing_team is None:
        raise HTTPException(status_code=404, detail="Team not found.")
    if existing_team.id != team_id:
        raise HTTPException(status_code=403, detail="You are not in the team.")
    await cruds_raid.update_team(team_id, team, db)
    updated_team = await cruds_raid.get_team_by_id(team_id, db)
    await post_update_actions(updated_team, db)


@module.router.delete(
    "/raid/teams/{team_id}",
    status_code=204,
)
async def delete_team(
    team_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.raid_admin)),
):
    """
    Delete a team
    """
    team = await cruds_raid.get_team_by_id(team_id, db)
    if not team:
        raise HTTPException(status_code=403, detail="This team does not exists")
    await cruds_raid.delete_team(team_id, db)
    if team.file_id:
        drive_file_manager.delete_file(team.file_id)
        if team.captain.security_file.file_id:
            drive_file_manager.delete_file(team.captain.security_file.file_id)
        if team.second and team.second.security_file.file_id:
            drive_file_manager.delete_file(team.second.security_file.file_id)


@module.router.delete(
    "/raid/teams",
    status_code=204,
)
async def delete_all_teams(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.raid_admin)),
):
    """
    Delete all teams
    """
    await cruds_raid.delete_all_teams(db)


@module.router.post(
    "/raid/participant/{participant_id}/document",
    response_model=schemas_raid.Document,
    status_code=201,
)
async def create_document(
    participant_id: str,
    document: schemas_raid.DocumentBase,
    user: models_core.CoreUser = Depends(is_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a document
    """
    if not await cruds_raid.are_user_in_the_same_team(participant_id, user.id, db):
        raise HTTPException(status_code=403, detail="You are not the participant.")

    saved_document = await cruds_raid.get_document_by_id(document.id, db)
    if not saved_document:
        raise HTTPException(status_code=404, detail="Document not found.")

    document_update = schemas_raid.DocumentUpdate(
        name=document.name,
        type=document.type,
    )
    await cruds_raid.update_document(document.id, document_update, db)

    document_type_id = "id_card_id"

    if document.type == "medicalCertificate":
        document_type_id = "medical_certificate_id"
    elif document.type == "raidRules":
        document_type_id = "raid_rules_id"
    elif document.type == "studentCard":
        document_type_id = "student_card_id"
    elif document.type == "parentAuthorization":
        document_type_id = "parent_authorization_id"

    await cruds_raid.assign_document(
        participant_id=participant_id,
        document_id=document.id,
        document_key=document_type_id,
        db=db,
    )

    team = await cruds_raid.get_team_by_participant_id(participant_id, db)
    await post_update_actions(team, db)
    return await cruds_raid.get_document_by_id(document.id, db)


@module.router.post(
    "/raid/document",
    response_model=schemas_raid.DocumentCreation,
    status_code=201,
)
async def upload_document(
    file: UploadFile = File(...),
    request_id: str = Depends(get_request_id),
    user: models_core.CoreUser = Depends(is_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload a document
    """
    document_id = str(uuid.uuid4())

    await save_file_as_data(
        upload_file=file,
        directory="raid",
        filename=str(document_id),
        request_id=request_id,
        max_file_size=50 * 1024 * 1024,  # TODO : Change this value
        accepted_content_types=[
            ContentType.jpg,
            ContentType.png,
            ContentType.webp,
            ContentType.pdf,
        ],  # TODO : Change this value
    )

    model_document = models_raid.Document(
        uploaded_at=datetime.now(UTC).date(),
        validation=DocumentValidation.pending,
        id=document_id,
        # Default values, updated with the document assignation
        name=file.filename,
        type=DocumentType.idCard,
    )

    await cruds_raid.create_document(model_document, db)

    return schemas_raid.DocumentCreation(id=document_id)


@module.router.get(
    "/raid/document/{document_id}",
    response_class=FileResponse,
    status_code=200,
)
async def read_document(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user),
):
    """
    Read a document
    """

    document = await cruds_raid.get_document_by_id(document_id, db)

    if not document:
        raise HTTPException(status_code=404, detail="Document not found.")

    participant = await cruds_raid.get_user_by_document_id(document_id, db)
    if not participant:
        raise HTTPException(
            status_code=404,
            detail="Participant owning the document not found.",
        )

    if not await cruds_raid.are_user_in_the_same_team(
        user.id,
        participant.id,
        db,
    ) and not is_user_member_of_an_allowed_group(user, [GroupType.raid_admin]):
        raise HTTPException(
            status_code=403,
            detail="You are not the owner of this document.",
        )

    return get_file_from_data(
        default_asset="assets/images/default_advert.png",  # TODO: get a default document
        directory="raid",
        filename=str(document_id),
    )


@module.router.post(
    "/raid/document/{document_id}/validate",
    status_code=204,
)
async def validate_document(
    document_id: str,
    validation: DocumentValidation,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.raid_admin)),
):
    """
    Validate a document
    """
    await cruds_raid.update_document_validation(document_id, validation, db)
    team = await cruds_raid.get_team_by_participant_id(user.id, db)
    await post_update_actions(team, db)


@module.router.post(
    "/raid/security_file/",
    response_model=schemas_raid.SecurityFile,
    status_code=201,
)
async def set_security_file(
    security_file: schemas_raid.SecurityFileBase,
    participant_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user),
):
    """
    Confirm security file
    """
    if not await cruds_raid.are_user_in_the_same_team(user.id, participant_id, db):
        raise HTTPException(status_code=403, detail="You are not the participant.")
    existing_security_file = await cruds_raid.get_security_file_by_security_id(
        security_file.id,
        db,
    )
    if existing_security_file:
        await cruds_raid.update_security_file(security_file, db)
        team = await cruds_raid.get_team_by_participant_id(user.id, db)
        participant = await cruds_raid.get_participant_by_id(participant_id, db)
        if team and participant:
            await save_security_file(participant, team.number, db)
        return await cruds_raid.get_security_file_by_security_id(
            security_file.id,
            db,
        )
    model_security_file = models_raid.SecurityFile(
        **security_file.model_dump(),
    )
    created_security_file = await cruds_raid.add_security_file(model_security_file, db)
    team = await cruds_raid.get_team_by_participant_id(user.id, db)
    participant = await cruds_raid.get_participant_by_id(participant_id, db)
    if team and participant:
        await save_security_file(participant, team.number, db)
    return created_security_file


@module.router.post(
    "/raid/participant/{participant_id}/security_file",
    status_code=204,
)
async def assign_security_file(
    participant_id: str,
    security_file_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user),
):
    """
    Assign security file
    """
    if not await cruds_raid.are_user_in_the_same_team(user.id, participant_id, db):
        raise HTTPException(status_code=403, detail="You are not the participant.")
    await cruds_raid.assign_security_file(participant_id, security_file_id, db)
    team = await cruds_raid.get_team_by_participant_id(user.id, db)
    await post_update_actions(team, db)


@module.router.post(
    "/raid/participant/{participant_id}/payment",
    status_code=204,
)
async def confirm_payment(
    participant_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.raid_admin)),
):
    """
    Confirm payment
    """
    await cruds_raid.confirm_payment(participant_id, db)
    team = await cruds_raid.get_team_by_participant_id(participant_id, db)
    await post_update_actions(team, db)


@module.router.post(
    "/raid/participant/{participant_id}/t_shirt_payment",
    status_code=204,
)
async def confirm_t_shirt_payment(
    participant_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.raid_admin)),
):
    """
    Confirm T shirt payment
    """
    participant = await cruds_raid.get_participant_by_id(participant_id, db)
    if not participant.t_shirt_size:
        raise HTTPException(status_code=403, detail="T shirt size not set.")
    await cruds_raid.confirm_t_shirt_payment(participant_id, db)
    team = await cruds_raid.get_team_by_participant_id(participant_id, db)
    await post_update_actions(team, db)


@module.router.post(
    "/raid/participant/{participant_id}/honour",
    status_code=204,
)
async def validate_attestation_on_honour(
    participant_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user),
):
    """
    Validate attestation on honour
    """
    if participant_id != user.id:
        raise HTTPException(status_code=403, detail="You are not the participant")
    await cruds_raid.validate_attestation_on_honour(participant_id, db)
    team = await cruds_raid.get_team_by_participant_id(participant_id, db)
    await post_update_actions(team, db)


@module.router.post(
    "/raid/teams/{team_id}/invite",
    response_model=schemas_raid.InviteToken,
    status_code=201,
)
async def create_invite_token(
    team_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user),
):
    """
    Create an invite token
    """
    team = await cruds_raid.get_team_by_participant_id(user.id, db)

    if not team:
        raise HTTPException(status_code=404, detail="Team not found.")

    if team.id != team_id:
        raise HTTPException(status_code=403, detail="You are not in the team.")

    existing_invite_token = await cruds_raid.get_invite_token_by_team_id(team_id, db)

    if existing_invite_token:
        return existing_invite_token

    invite_token = models_raid.InviteToken(
        id=str(uuid.uuid4()),
        team_id=team_id,
        token=get_random_string(length=10),
    )

    return await cruds_raid.create_invite_token(invite_token, db)


@module.router.post(
    "/raid/teams/join/{token}",
    status_code=204,
)
async def join_team(
    token: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user),
):
    """
    Join a team
    """
    invite_token = await cruds_raid.get_invite_token_by_token(token, db)

    if not invite_token:
        raise HTTPException(status_code=404, detail="Invite token not found.")

    user_team = await cruds_raid.get_team_by_participant_id(user.id, db)

    if user_team:
        if user_team.second_id:
            raise HTTPException(status_code=403, detail="You are already in a team.")

        if user_team.file_id:
            drive_file_manager.delete_file(user_team.file_id)
        await cruds_raid.delete_team(user_team.id, db)

    team = await cruds_raid.get_team_by_id(invite_token.team_id, db)

    if not team:
        raise HTTPException(status_code=404, detail="Team not found.")

    if team.second_id:
        raise HTTPException(status_code=403, detail="Team is already full.")

    if team.captain_id == user.id:
        raise HTTPException(
            status_code=403,
            detail="You are already the captain of this team.",
        )

    await cruds_raid.update_team_second_id(team.id, user.id, db)
    await post_update_actions(team, db)
    await cruds_raid.delete_invite_token(invite_token.id, db)


@module.router.post(
    "/raid/teams/{team_id}/kick/{participant_id}",
    response_model=schemas_raid.Team,
    status_code=201,
)
async def kick_team_member(
    team_id: str,
    participant_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.raid_admin)),
):
    """
    Leave a team
    """
    team = await cruds_raid.get_team_by_id(team_id, db)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found.")
    if team.captain_id == participant_id:
        if not team.second_id:
            raise HTTPException(
                status_code=403,
                detail="You can not kick the only member of the team.",
            )
        await cruds_raid.update_team_captain_id(
            team_id,
            team.second_id,
            db,
        )
    elif team.second_id != participant_id:
        raise HTTPException(status_code=404, detail="Participant not found.")
    await cruds_raid.update_team_second_id(team_id, None, db)
    await post_update_actions(team, db)
    return await cruds_raid.get_team_by_id(team_id, db)


@module.router.post(
    "/raid/teams/merge",
    response_model=schemas_raid.Team,
    status_code=201,
)
async def merge_teams(
    team1_id: str,
    team2_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.raid_admin)),
):
    """
    Merge two teams
    """
    team1 = await cruds_raid.get_team_by_id(team1_id, db)
    team2 = await cruds_raid.get_team_by_id(team2_id, db)
    if not team1 or not team2:
        raise HTTPException(status_code=404, detail="Team not found.")
    if team1.second_id or team2.second_id:
        raise HTTPException(status_code=403, detail="One of the team is full.")
    if team1.captain_id == team2.captain_id:
        raise HTTPException(status_code=403, detail="Teams are the same.")
    new_name = f"{team1.name} & {team2.name}"
    new_difficulty = team1.difficulty if team1.difficulty == team2.difficulty else None
    new_meeting_place = (
        team1.meeting_place if team1.meeting_place == team2.meeting_place else None
    )
    new_number = (
        min(team1.number, team2.number) if team1.number and team2.number else None
    )
    team_update: schemas_raid.TeamUpdate = schemas_raid.TeamUpdate(
        name=new_name,
        difficulty=new_difficulty,
        meeting_place=new_meeting_place,
        number=new_number,
    )
    await cruds_raid.update_team(
        team1_id,
        team_update,
        db,
    )
    await cruds_raid.update_team_second_id(team1_id, team2.captain_id, db)
    await cruds_raid.delete_team(team2_id, db)
    if team2.file_id:
        drive_file_manager.delete_file(team2.file_id)
    await post_update_actions(team1, db)
    return await cruds_raid.get_team_by_id(team1_id, db)


@module.router.get(
    "/raid/information",
    response_model=schemas_raid.RaidInformation,
    status_code=200,
)
async def get_raid_information(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user),
):
    """
    Get raid information
    """
    return await get_core_data(schemas_raid.RaidInformation, db)


@module.router.patch(
    "/raid/information",
    status_code=204,
)
async def update_raid_information(
    raid_information: schemas_raid.RaidInformation,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.raid_admin)),
):
    """
    Update raid information
    """
    await set_core_data(raid_information, db)
    if raid_information.raid_start_date:
        participants = await cruds_raid.get_all_participants(db)
        for participant in participants:
            is_minor = (
                date(
                    participant.birthday.year + 18,
                    participant.birthday.month,
                    participant.birthday.day,
                )
                > raid_information.raid_start_date
                if participant.birthday
                else False
            )
            await cruds_raid.update_participant_minority(participant.id, is_minor, db)


@module.router.patch(
    "/raid/drive",
    status_code=204,
)
async def update_drive_folders(
    drive_folders: schemas_raid.RaidDriveFoldersCreation,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.raid_admin)),
):
    """
    Update drive folders
    """
    schemas_folders = await get_core_data(schemas_raid.RaidDriveFolders, db)
    schemas_folders = schemas_raid.RaidDriveFolders(
        parent_folder_id=drive_folders.parent_folder_id,
        registering_folder_id=None,
        security_folder_id=None,
    )
    await set_core_data(schemas_folders, db)


@module.router.get(
    "/raid/drive",
    response_model=schemas_raid.RaidDriveFoldersCreation,
    status_code=200,
)
async def get_drive_folders(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.raid_admin)),
):
    """
    Get drive folders
    """
    return await get_core_data(schemas_raid.RaidDriveFolders, db)


@module.router.get(
    "/raid/price",
    response_model=schemas_raid.RaidPrice,
    status_code=200,
)
async def get_raid_price(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user),
):
    """
    Get raid price
    """
    return await get_core_data(schemas_raid.RaidPrice, db)


@module.router.patch(
    "/raid/price",
    status_code=204,
)
async def update_raid_price(
    raid_price: schemas_raid.RaidPrice,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.raid_admin)),
):
    """
    Update raid price
    """
    await set_core_data(raid_price, db)


@module.router.get(
    "/raid/pay",
    response_model=schemas_raid.PaymentUrl,
    status_code=201,
)
async def get_payment_url(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user),
    settings: Settings = Depends(get_settings),
):
    """
    Get payment url
    """
    raid_prices = await get_core_data(schemas_raid.RaidPrice, db)
    if not raid_prices.student_price or not raid_prices.t_shirt_price:
        raise HTTPException(status_code=404, detail="Prices not set.")
    price = 0
    checkout_name = ""
    participant = await cruds_raid.get_participant_by_id(user.id, db)
    if not participant.payment:
        price += raid_prices.student_price
        checkout_name += "Inscription Raid"
    if participant.t_shirt_size and not participant.t_shirt_payment:
        price += raid_prices.t_shirt_price
        if not participant.payment:
            checkout_name += " + "
        checkout_name += "T Shirt taille" + participant.t_shirt_size.value
    payment_tool = PaymentTool(settings=settings)
    checkout = await payment_tool.init_checkout(
        module="Raid",
        helloasso_slug="AEECL",
        checkout_amount=price,
        checkout_name=checkout_name,
        redirection_uri=settings.RAID_PAYMENT_REDIRECTION_URL,
        payer_user=user,
        db=db,
    )
    return schemas_raid.PaymentUrl(
        url=checkout.payment_url,
    )
