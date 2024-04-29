import logging
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.cruds import cruds_raid
from app.dependencies import get_db, get_request_id, is_user_a_member
from app.models import models_core, models_raid
from app.schemas import schemas_raid
from app.utils.tools import get_file_from_data, save_file_as_data
from app.utils.types import standard_responses
from app.utils.types.tags import Tags

router = APIRouter()

hyperion_error_logger = logging.getLogger("hyperion.error")


@router.get(
    "/raid/participant/{participant_id}",
    response_model=schemas_raid.Participant,
    status_code=200,
    tags=[Tags.raid],
)
async def get_participant_by_id(
    participant_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get a participant by id
    """
    participant = await cruds_raid.get_participant_by_id(participant_id, db)
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found.")
    return participant


@router.post(
    "/raid/participant",
    response_model=schemas_raid.Participant,
    status_code=201,
    tags=[Tags.raid],
)
async def create_participant(
    participant: schemas_raid.ParticipantBase,
    user: models_core.CoreUser = Depends(is_user_a_member),
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


@router.patch(
    "/raid/participant/{participant_id}",
    status_code=204,
    tags=[Tags.raid],
)
async def update_participant(
    participant_id: str,
    participant: schemas_raid.ParticipantUpdate,
    user: models_core.CoreUser = Depends(is_user_a_member),
    db: AsyncSession = Depends(get_db),
):
    """
    Update a participant
    """
    # If the user is not a participant, return an error
    if not await cruds_raid.is_user_a_participant(participant_id, db):
        raise HTTPException(status_code=403, detail="You are not a participant.")

    # If the user is not the participant, return an error
    if participant_id != user.id:
        raise HTTPException(status_code=403, detail="You are not the participant.")

    await cruds_raid.update_participant(participant_id, participant, db)


@router.post(
    "/raid/team",
    response_model=schemas_raid.TeamBase,
    status_code=201,
    tags=[Tags.raid],
)
async def create_team(
    team: schemas_raid.TeamBase,
    user: models_core.CoreUser = Depends(is_user_a_member),
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
        number=0,
        captain_id=user.id,
        second_id=None,
        validation_progress=0.0,
    )
    return await cruds_raid.create_team(db_team, db)


@router.get(
    "/raid/participant/{participant_id}/team",
    response_model=schemas_raid.Team,
    status_code=200,
    tags=[Tags.raid],
)
async def get_team_by_participant_id(
    participant_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get a team by participant id
    """
    # If the user is not a participant, return an error
    if not await cruds_raid.is_user_a_participant(participant_id, db):
        raise HTTPException(status_code=403, detail="You are not a participant.")

    participant_team = await cruds_raid.get_team_by_participant_id(participant_id, db)
    # If the user does not have a team, return an error
    if not participant_team:
        raise HTTPException(status_code=404, detail="You do not have a team.")
    return participant_team


@router.get(
    "/raid/team/all",
    response_model=list[schemas_raid.TeamPreview],
    status_code=200,
    tags=[Tags.raid],
)
async def get_all_teams(
    db: AsyncSession = Depends(get_db),
):
    """
    Get all teams
    """
    return await cruds_raid.get_all_teams(db)


@router.get(
    "/raid/team/{team_id}",
    response_model=schemas_raid.Team,
    status_code=200,
    tags=[Tags.raid],
)
async def get_team_by_id(
    team_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get a team by id
    """
    return await cruds_raid.get_team_by_id(team_id, db)


@router.patch(
    "/raid/team/{team_id}",
    status_code=204,
    tags=[Tags.raid],
)
async def update_team(
    team_id: str,
    team: schemas_raid.TeamUpdate,
    db: AsyncSession = Depends(get_db),
):
    """
    Update a team
    """
    await cruds_raid.update_team(team_id, team, db)


@router.delete(
    "/raid/team/{team_id}",
    status_code=204,
    tags=[Tags.raid],
)
async def delete_team(
    team_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a team
    """
    await cruds_raid.delete_team(team_id, db)


@router.delete(
    "/raid/team/all",
    status_code=204,
    tags=["raid"],
)
async def delete_all_teams(
    db: AsyncSession = Depends(get_db),
):
    """
    Delete all teams
    """
    await cruds_raid.delete_all_teams(db)


@router.post(
    "/raid/participant/{participant_id}/document",
    status_code=204,
    tags=["raid"],
)
async def create_document(
    document: schemas_raid.Document,
    db: AsyncSession = Depends(get_db),
):
    """
    Create a document
    """
    await cruds_raid.create_document(document, db)


@router.post(
    "/raid/document/{document_id}",
    response_model=standard_responses.Result,
    status_code=201,
    tags=["raid"],
)
async def upload_document(
    document_id: str,
    image: UploadFile = File(...),
    request_id: str = Depends(get_request_id),
):
    """
    Upload a document
    """
    await save_file_as_data(
        image=image,
        directory="raid",
        filename=str(document_id),
        request_id=request_id,
        max_file_size=4 * 1024 * 1024,  # TODO : Change this value
        accepted_content_types=[
            "image/jpeg",
            "image/png",
            "image/webp",
        ],  # TODO : Change this value
    )

    return standard_responses.Result(success=True)


@router.get(
    "/raid/document/{document_id}",
    response_class=FileResponse,
    status_code=200,
    tags=["raid"],
)
async def read_document(
    document_id: str,
):
    """
    Read a document
    """
    return get_file_from_data(
        default_asset="assets/images/default_advert.png",
        directory="raid",
        filename=str(document_id),
    )


@router.patch(
    "/raid/participant/{participant_id}/document/{document_id}",
    status_code=204,
    tags=["raid"],
)
async def update_document(
    document_id: str,
    document: schemas_raid.DocumentBase,
    db: AsyncSession = Depends(get_db),
):
    """
    Update a document
    """
    await cruds_raid.update_document(document_id, document, db)


@router.delete(
    "/raid/participant/{participant_id}/document/{document_id}",
    status_code=204,
    tags=["raid"],
)
async def delete_document(
    document_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a document
    """
    await cruds_raid.delete_document(document_id, db)


@router.post(
    "/raid/participant/{participant_id}/payment",
    response_model=schemas_raid.Participant,
    status_code=201,
    tags=["raid"],
)
async def confirm_payment(
    participant_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Confirm payment
    """
    return await cruds_raid.confirm_payment(participant_id, db)


@router.post(
    "/raid/participant/{participant_id}/honour",
    status_code=204,
    tags=["raid"],
)
async def validate_attestation_on_honour(
    participant_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Validate attestation on honour
    """
    return await cruds_raid.validate_attestation_on_honour(participant_id, db)
