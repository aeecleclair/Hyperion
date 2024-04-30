import logging
import uuid
from datetime import datetime

from fastapi import Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import models_core, standard_responses
from app.core.groups.groups_type import GroupType
from app.core.module import Module
from app.dependencies import (
    get_db,
    get_request_id,
    is_user,
    is_user_a_member_of,
)
from app.modules.raid import cruds_raid, models_raid, schemas_raid
from app.modules.raid.utils.drive.drive_file_manager import DriveFileManager
from app.modules.raid.utils.pdf.pdf_writer import PDFWriter
from app.utils.tools import (
    get_file_from_data,
    get_random_string,
    is_user_member_of_an_allowed_group,
    save_file_as_data,
)

hyperion_error_logger = logging.getLogger("hyperion.error")


module = Module(
    root="raid",
    tag="Raid",
    default_allowed_groups_ids=[GroupType.student, GroupType.staff],
)


drive_file_manager = DriveFileManager()


async def save_team_info(team: schemas_raid.Team, db: AsyncSession) -> str:
    pdf_writer = PDFWriter()
    file_path = pdf_writer.write_team(team)
    file_name = file_path.split("/")[-1]
    if team.file_id:
        file_id = drive_file_manager.replace_file(file_path, team.file_id)
    else:
        file_id = drive_file_manager.upload_file(file_path, file_name)
    await cruds_raid.update_team_file_id(team.id, file_id, db)
    pdf_writer.clear_pdf()


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
        user, [GroupType.raid_admin]
    ):
        raise HTTPException(
            status_code=403, detail="You can not get data of another user"
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

    db_participant = models_raid.Participant(**participant.__dict__, id=user.id)
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

    await cruds_raid.update_participant(participant_id, participant, db)
    team = await cruds_raid.get_team_by_participant_id(participant_id, db)
    await save_team_info(team, db)


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
    await save_team_info(created_team, db)
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
    await save_team_info(team, db)


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
    await cruds_raid.delete_team(team_id, db)
    drive_file_manager.delete_file(team.file_id)


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
    document: schemas_raid.DocumentCreation,
    user: models_core.CoreUser = Depends(is_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a document
    """
    if not await cruds_raid.are_user_in_the_same_team(participant_id, db):
        raise HTTPException(status_code=403, detail="You are not the participant.")

    # existing_document = await cruds_raid.get_document_by_id(document.id, db)

    # if existing_document:
    #     pass  # TODO: Delete the existing document

    document = models_raid.Document(
        uploaded_at=datetime.now().date(),
        validated=False,
        id=document.id,
        name=document.name,
        type=document.type,
    )

    await cruds_raid.create_document(document, db)

    document_type_id = "id_card_id"

    if document.type == "medicalCertificate":
        document_type_id = "medical_certificate_id"
    elif document.type == "raidRules":
        document_type_id = "raid_rules_id"
    elif document.type == "studentCard":
        document_type_id = "student_card_id"

    await cruds_raid.assign_document(
        participant_id=participant_id,
        document_id=document.id,
        document_key=document_type_id,
        db=db,
    )

    team = await cruds_raid.get_team_by_participant_id(participant_id, db)
    await save_team_info(team, db)
    return document


@module.router.post(
    "/raid/document/{document_id}",
    response_model=standard_responses.Result,
    status_code=201,
)
async def upload_document(
    document_id: str,
    image: UploadFile = File(...),
    request_id: str = Depends(get_request_id),
    user: models_core.CoreUser = Depends(is_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload a document
    """
    # document_obj = await cruds_raid.get_document_by_id(document_id=document_id, db=db)
    # if not document_obj:
    #     raise HTTPException(status_code=404, detail="Document not found.")
    # participant = await cruds_raid.get_user_by_document_id(
    #     document_id=document_id, db=db
    # )
    # if not participant:
    #     raise HTTPException(
    #         status_code=404, detail="Participant owning hte document not found."
    #     )
    # if not participant.id == user.id:
    #     raise HTTPException(
    #         status_code=403, detail="You are not the owner of this document."
    #     )

    await save_file_as_data(
        upload_file=image,
        directory="raid",
        filename=str(document_id),
        request_id=request_id,
        max_file_size=50 * 1024 * 1024,  # TODO : Change this value
        accepted_content_types=[
            "image/jpeg",
            "image/png",
            "image/webp",
            "application/pdf",
        ],  # TODO : Change this value
    )

    await cruds_raid.mark_document_as_newly_updated(document_id=document_id, db=db)

    return standard_responses.Result(success=True)


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
            status_code=404, detail="Participant owning the document not found."
        )

    if not cruds_raid.are_user_in_the_same_team(
        user.id, participant.id, db
    ) and not is_user_member_of_an_allowed_group(user, [GroupType.raid_admin]):
        raise HTTPException(
            status_code=403, detail="You are not the owner of this document."
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
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.raid_admin)),
):
    """
    Validate a document
    """
    await cruds_raid.validate_document(document_id, db)
    team = await cruds_raid.get_team_by_participant_id(user.id, db)
    await save_team_info(team, db)


@module.router.post(
    "/raid/security_file/",
    response_model=schemas_raid.SecurityFile,
    status_code=201,
)
async def set_security_file(
    security_file: schemas_raid.SecurityFile,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user),
):
    """
    Confirm security file
    """
    existing_security_file = await cruds_raid.get_security_file_by_security_id(
        security_file.id, db
    )
    if existing_security_file:
        await cruds_raid.update_security_file(security_file, db)
    else:
        model_security_file = models_raid.SecurityFile(
            **security_file.model_dump(),
        )
        await cruds_raid.add_security_file(model_security_file, db)
    return security_file


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
    result = await cruds_raid.assign_security_file(participant_id, security_file_id, db)
    team = await cruds_raid.get_team_by_participant_id(user.id, db)
    await save_team_info(team, db)
    return result


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
    team = await cruds_raid.get_team_by_participant_id(participant_id, db)
    await save_team_info(team, db)
    return await cruds_raid.confirm_payment(participant_id, db)


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
    team = await cruds_raid.get_team_by_participant_id(participant_id, db)
    await save_team_info(team, db)
    return await cruds_raid.validate_attestation_on_honour(participant_id, db)


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

        drive_file_manager.delete_file(user_team.file_id)
        await cruds_raid.delete_team(user_team.id, db)

    team = await cruds_raid.get_team_by_id(invite_token.team_id, db)

    if not team:
        raise HTTPException(status_code=404, detail="Team not found.")

    if team.second_id:
        raise HTTPException(status_code=403, detail="Team is already full.")

    if team.captain_id == user.id:
        raise HTTPException(
            status_code=403, detail="You are already the captain of this team."
        )

    await cruds_raid.update_team_second_id(team.id, user.id, db)
    await save_team_info(team, db)
    await cruds_raid.delete_invite_token(invite_token.id, db)
