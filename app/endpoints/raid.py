import logging

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.cruds import cruds_raid
from app.dependencies import get_db, get_request_id
from app.schemas import schemas_raid
from app.utils.tools import get_file_from_data, save_file_as_data
from app.utils.types import standard_responses

router = APIRouter()

hyperion_error_logger = logging.getLogger("hyhperion.error")


@router.get(
    "/raid/participant/{participant_id}/team",
    response_model=schemas_raid.Team,
    status_code=200,
    tags=["raid"],
)
async def get_team_by_participant_id(
    participant_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get a team by participant id
    """
    return await cruds_raid.get_team_by_participant_id(participant_id, db)


@router.get(
    "/raid/teams",
    response_model=list[schemas_raid.TeamPreview],
    status_code=200,
    tags=["raid"],
)
async def get_all_teams(
    db: AsyncSession = Depends(get_db),
):
    """
    Get all teams
    """
    return await cruds_raid.get_all_teams(db)


@router.post(
    "/raid/team",
    response_model=schemas_raid.TeamPreview,
    status_code=201,
    tags=["raid"],
)
async def create_team(
    team: schemas_raid.TeamBase,
    db: AsyncSession = Depends(get_db),
):
    """
    Create a team
    """
    return await cruds_raid.create_team(team, db)


@router.get(
    "/raid/team/{team_id}",
    response_model=schemas_raid.Team,
    status_code=200,
    tags=["raid"],
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
    tags=["raid"],
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
    tags=["raid"],
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
    "/raid/teams",
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
    status_code=204,
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
    response_model=FileResponse,
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


@router.get(
    "/raid/participant/{participant_id}/honour",
    response_model=schemas_raid.Participant,
    status_code=200,
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
