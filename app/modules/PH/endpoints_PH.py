import uuid

from fastapi import Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import models_core, standard_responses
from app.core.groups.groups_type import GroupType
from app.core.module import Module
from app.dependencies import (
    get_db,
    get_request_id,
    is_user_a_member,
    is_user_a_member_of,
)
from app.modules.PH import cruds_PH, models_PH, schemas_PH
from app.utils.tools import get_file_from_data, save_file_as_data

module = Module(
    root="PH",
    tag="PH",
    default_allowed_groups_ids=[GroupType.student],
)


@module.router.get(
    "/PH/{journal_id}/pdf",
    response_class=FileResponse,
    status_code=200,
)
async def get_journal_pdf(
    journal_id: str,
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    return get_file_from_data(
        default_asset="assets/pdf/default_PDF.pdf",
        directory="PH",
        filename=str(journal_id),
    )


@module.router.get(
    "/PH/",
    response_model=list[schemas_PH.Journal],
    status_code=200,
)
async def get_journals(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    result = await cruds_PH.get_journals(db=db)
    return result


@module.router.post(
    "/PH/",
    response_model=schemas_PH.Journal,
    status_code=201,
)
async def create_journal(
    journal: schemas_PH.Journal,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.PH)),
):
    """
    Create a new journal.
    """

    try:
        journal_db = models_PH.Journal(
            id=str(uuid.uuid4()),
            name=journal.name,
            release_date=journal.release_date,
        )

        return await cruds_PH.create_journal(journal=journal_db, db=db)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))


@module.router.post(
    "/PH/{journal_id}/pdf",
    response_model=standard_responses.Result,
    status_code=201,
)
async def create_journal_pdf(
    journal_id: str,
    pdf: UploadFile = File(...),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.PH)),
    request_id: str = Depends(get_request_id),
    db: AsyncSession = Depends(get_db),
):
    journal = await cruds_PH.get_journal_by_id(db=db, journal_id=journal_id)
    if journal is None:
        raise HTTPException(
            status_code=404,
            detail="The journal does not exist.",
        )

    await save_file_as_data(
        image=pdf,
        directory="PH",
        filename=str(journal_id),
        request_id=request_id,
        max_file_size=10 * 1024 * 1024,
        accepted_content_types=["application/pdf"],
    )

    return standard_responses.Result(success=True)
