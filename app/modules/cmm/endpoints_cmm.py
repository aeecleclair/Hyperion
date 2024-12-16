import uuid
from datetime import UTC, datetime

from fastapi import Depends, HTTPException, status
from fastapi.datastructures import UploadFile
from fastapi import File
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.routing import request_response

from app.core import models_core
from app.core.groups.groups_type import AccountType, GroupType
from app.dependencies import (
    get_db,
    get_request_id,
    is_user,
    is_user_a_member,
    is_user_in,
)
from app.modules.cmm import cruds_cmm, models_cmm, schemas_cmm, types_cmm
from app.types.content_type import ContentType
from app.types.module import Module
from app.utils.tools import save_file_as_data

module = Module(
    root="cmm",
    tag="Centrale Mega Meme",
    default_allowed_account_types=[AccountType.student],
)


@module.router.get(
    "/memes/{n_page}",
    response_model=list[schemas_cmm.Meme],
    status_code=200,
)
async def get_memes(
    sort_by: str | None,
    db: AsyncSession = Depends(get_db),
    n_page: int = 1,
):
    """
    Get a page of memes according to the asked sort
    """
    if n_page < 1:
        raise HTTPException(
            status_code=204,
            detail="Invalid page number",
        )

    match sort_by:
        case types_cmm.MemeSort.best:
            meme_page = await cruds_cmm.get_memes_by_votes(
                db=db,
                descending=True,
                n_page=n_page,
            )
        case types_cmm.MemeSort.worst:
            meme_page = await cruds_cmm.get_memes_by_votes(
                db=db,
                descending=False,
                n_page=n_page,
            )
        case types_cmm.MemeSort.trending:
            meme_page = await cruds_cmm.get_trending_memes(
                db=db,
                n_page=n_page,
            )
        case types_cmm.MemeSort.newest:
            meme_page = await cruds_cmm.get_memes_by_date(
                db=db,
                descending=True,
                n_page=n_page,
            )
        case types_cmm.MemeSort.oldest:
            meme_page = await cruds_cmm.get_memes_by_date(
                db=db,
                descending=False,
                n_page=n_page,
            )
        case _:
            raise HTTPException(status_code=204, detail="Invalid sort method")

    return meme_page


@module.router.post(
    "/memes",
    response_model=schemas_cmm.Meme,
    status_code=201,
)
async def add_meme(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user()),
    image: UploadFile = File(...),
    request_id: str = Depends(get_request_id),
):
    """
    Add a new meme
    """
    try:
        meme_id = uuid.uuid4()
        meme = models_cmm.Meme(
            id=meme_id,
            user_id=user.id,
            creation_time=datetime.now(UTC),
            vote_score=0,
            votes=[],
            status=types_cmm.MemeStatus.neutral,
        )
        cruds_cmm.add_meme_in_DB(db=db, meme=meme)
        await db.commit()
        await save_file_as_data(
            upload_file=image,
            directory="profile-pictures",
            filename=str(meme_id),
            request_id=request_id,
            max_file_size=4 * 1024 * 1024,
            accepted_content_types=[
                ContentType.jpg,
                ContentType.png,
                ContentType.webp,
            ],
        )

    except Exception:
        await db.rollback()
        raise
