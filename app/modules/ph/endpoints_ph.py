import uuid

import fitz
from fastapi import Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from PIL import Image
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
from app.modules.ph import cruds_ph, models_ph, schemas_ph
from app.utils.tools import delete_file_from_data, get_file_from_data, save_file_as_data

module = Module(
    root="ph",
    tag="ph",
    default_allowed_groups_ids=[GroupType.student],
)


@module.router.get(
    "/ph/{paper_id}/pdf",
    response_class=FileResponse,
    status_code=200,
)
async def get_paper_pdf(
    paper_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    paper = await cruds_ph.get_paper_by_id(db=db, paper_id=paper_id)
    if paper is None:
        raise HTTPException(
            status_code=404,
            detail="The paper does not exist.",
        )

    return get_file_from_data(
        default_asset="assets/pdf/default_PDF.pdf",
        directory="ph/pdf",
        filename=str(paper_id),
    )


@module.router.get(
    "/ph/",
    response_model=list[schemas_ph.PaperComplete],
    status_code=200,
)
async def get_papers(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Return all editions, sorted from the latest to the oldest
    """
    result = await cruds_ph.get_papers(
        db=db,
    )  # Return papers from the latest to the oldest
    return result


@module.router.post(
    "/ph/",
    response_model=schemas_ph.PaperComplete,
    status_code=201,
)
async def create_paper(
    paper: schemas_ph.PaperBase,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.ph)),
):
    """Create a new paper."""

    paper_complete = schemas_ph.PaperComplete(
        id=str(uuid.uuid4()),
        **paper.model_dump(),
    )
    try:
        paper_db = models_ph.Paper(
            id=paper_complete.id,
            name=paper_complete.name,
            release_date=paper_complete.release_date,
        )
        return await cruds_ph.create_paper(paper=paper_db, db=db)
    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )


@module.router.post(
    "/ph/{paper_id}/pdf",
    response_model=standard_responses.Result,
    status_code=201,
)
async def create_paper_pdf(
    paper_id: str,
    pdf: UploadFile = File(...),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.ph)),
    request_id: str = Depends(get_request_id),
    db: AsyncSession = Depends(get_db),
):
    paper = await cruds_ph.get_paper_by_id(db=db, paper_id=paper_id)
    if paper is None:
        raise HTTPException(
            status_code=404,
            detail="The paper does not exist.",
        )

    await save_file_as_data(
        image=pdf,
        directory="ph/pdf",
        filename=str(paper_id),
        request_id=request_id,
        max_file_size=10 * 1024 * 1024,
        accepted_content_types=["application/pdf"],
    )

    return standard_responses.Result(success=True)


@module.router.patch(
    "/ph/{paper_id}",
    status_code=204,
)
async def update_paper(
    paper_id: str,
    paper_update: schemas_ph.PaperUpdate,
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.ph)),
    db: AsyncSession = Depends(get_db),
):
    paper = await cruds_ph.get_paper_by_id(paper_id=paper_id, db=db)
    if not paper:
        raise HTTPException(
            status_code=404,
            detail="Invalid paper_id",
        )

    await cruds_ph.update_paper(
        paper_id=paper_id,
        paper_update=paper_update,
        db=db,
    )


@module.router.delete(
    "/ph/{paper_id}",
    status_code=204,
)
async def delete_paper(
    paper_id: str,
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.ph)),
    db: AsyncSession = Depends(get_db),
):
    paper = await cruds_ph.get_paper_by_id(paper_id=paper_id, db=db)
    if not paper:
        raise HTTPException(
            status_code=404,
            detail="Invalid paper_id",
        )

    await cruds_ph.delete_paper(
        paper_id=paper_id,
        db=db,
    )


@module.router.delete(
    "/ph/{paper_id}/pdf",
    status_code=204,
)
async def delete_paper_pdf(
    paper_id: str,
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.ph)),
    db: AsyncSession = Depends(get_db),
):
    paper = await cruds_ph.get_paper_by_id(paper_id=paper_id, db=db)
    if not paper:
        raise HTTPException(
            status_code=404,
            detail="Invalid paper_id",
        )

    await delete_file_from_data(
        directory="ph/pdf",
        filename=str(paper_id),
    )


@module.router.get(
    "/ph/{paper_id}/cover",
    status_code=204,
)
async def get_cover(
    paper_id: str,
    user: models_core.CoreUser = Depends(is_user_a_member),
    db: AsyncSession = Depends(get_db),
):
    paper = await cruds_ph.get_paper_by_id(db=db, paper_id=paper_id)
    if paper is None:
        raise HTTPException(
            status_code=404,
            detail="The paper does not exist.",
        )

    paper_pdf = fitz.open(f"data/ph/pdf/{paper_id}.pdf")
    page = paper_pdf.load_page(0)
    pix = page.get_pixmap(matrix=fitz.Matrix(300 / 72, 300 / 72))
    cover = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    cover.save(f"data/ph/cover/{paper_id}.jpg", "JPG")
    paper_pdf.close()

    return get_file_from_data(
        default_asset="assets/images/default_cover.jpg",
        directory="ph/cover",
        filename=str(paper_id),
    )
