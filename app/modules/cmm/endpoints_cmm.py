import uuid
from datetime import UTC, datetime

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import models_core
from app.core.groups.groups_type import AccountType, GroupType
from app.dependencies import get_db, is_user_a_member, is_user_in
from app.modules.cmm import cruds_cmm, models_cmm, schemas_cmm, types_cmm
from app.types.module import Module

module = Module(
    root="cmm",
    tag="Centrale Mega Meme",
    default_allowed_account_types=[AccountType.student],
)


@module.router.get(
    "/flappybird/scores",
    response_model=list[schemas_cmm.Meme],
    status_code=200,
)
async def get_memes(
    sort_by: str | None,
    db: AsyncSession = Depends(get_db),
    n_page: int = 1,
):
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
