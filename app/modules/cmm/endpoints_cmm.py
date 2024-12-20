import uuid
from datetime import UTC, datetime

from fastapi import Depends, File, HTTPException
from fastapi.datastructures import UploadFile
from fastapi.responses import FileResponse
from pydantic import HttpUrl
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import models_core
from app.core.groups.groups_type import AccountType, GroupType
from app.dependencies import (
    get_db,
    get_request_id,
    is_user,
)
from app.modules.cmm import cruds_cmm, models_cmm, schemas_cmm, types_cmm
from app.types.content_type import ContentType
from app.types.module import Module
from app.utils.tools import (
    delete_file_from_data,
    get_file_from_data,
    is_user_member_of_an_allowed_group,
    save_file_as_data,
)

module = Module(
    root="cmm",
    tag="Centrale Mega Meme",
    default_allowed_account_types=[AccountType.student],
)


@module.router.get(
    "/memes",
    response_model=list[schemas_cmm.Meme],
    status_code=200,
)
async def get_memes(
    sort_by: str | None,
    db: AsyncSession = Depends(get_db),
    n_page: int = 1,
    user: models_core.CoreUser = Depends(is_user()),
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
                user_id=user.id,
            )
        case types_cmm.MemeSort.worst:
            meme_page = await cruds_cmm.get_memes_by_votes(
                db=db,
                descending=False,
                n_page=n_page,
                user_id=user.id,
            )
        case types_cmm.MemeSort.trending:
            meme_page = await cruds_cmm.get_trending_memes(
                db=db,
                n_page=n_page,
                user_id=user.id,
            )
        case types_cmm.MemeSort.newest:
            meme_page = await cruds_cmm.get_memes_by_date(
                db=db,
                descending=True,
                n_page=n_page,
                user_id=user.id,
            )
        case types_cmm.MemeSort.oldest:
            meme_page = await cruds_cmm.get_memes_by_date(
                db=db,
                descending=False,
                n_page=n_page,
                user_id=user.id,
            )
        case _:
            raise HTTPException(status_code=204, detail="Invalid sort method")

    # TODO: Doesnt work if vote doesnt exist for meme, missing key
    full_meme_page = [
        schemas_cmm.FullMeme(
            **meme.model_dump(),
            my_vote=types_cmm.compute_vote_value(meme_page["votes_map"][meme.id]),
        )
        for meme in meme_page["memes"]
    ]
    return full_meme_page


@module.router.get(
    "/memes/{meme_id}",
    status_code=200,
    response_model=schemas_cmm.FullMeme,
)
async def get_meme_by_id(
    meme_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user()),
):
    """
    Get a meme caracteristics using its id
    """
    meme = await cruds_cmm.get_meme_by_id(db=db, meme_id=meme_id)
    if meme is None:
        raise HTTPException(status_code=204, detail="The meme does not exist")

    my_vote = await cruds_cmm.get_vote(db=db, meme_id=meme.id, user_id=user.id)
    full_meme = schemas_cmm.FullMeme(
        my_vote=types_cmm.compute_vote_value(my_vote),
        **meme.model_dump(),
    )
    return full_meme


@module.router.get(
    "/memes/{meme_id}/img",
    status_code=200,
    response_model=FileResponse,
)
async def get_meme_image_by_id(
    meme_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Get a meme image using its id
    """
    meme = await cruds_cmm.get_meme_by_id(db=db, meme_id=meme_id)
    if meme is None:
        raise HTTPException(status_code=404, detail="The meme does not exist")

    # TODO: Change default asset
    return get_file_from_data(
        default_asset="assets/pdf/default_ph.pdf",
        directory="memes",
        filename=str(meme_id),
    )


@module.router.delete(
    "memes/{meme_id}",
    status_code=204,
)
async def delete_meme_by_id(
    meme_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user()),
):
    """
    Remove a meme from db
    Must be admin or author of meme
    """
    meme = await cruds_cmm.get_meme_by_id(db=db, meme_id=meme_id)
    if not meme:
        raise HTTPException(
            status_code=404,
            detail="Invalid meme_id",
        )
    if not (
        meme.user_id == user.id
        or is_user_member_of_an_allowed_group(user, [GroupType.admin])
    ):
        raise HTTPException(
            status_code=403,
            detail="You cannot remove a meme from another user",
        )
    try:
        await cruds_cmm.delete_meme_by_id(db=db, meme_id=meme_id)
        await delete_file_from_data(directory="meme", filename=str(meme_id))
        await db.commit()
    except Exception:
        await db.rollback()
        raise


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
        cruds_cmm.add_meme(db=db, meme=meme)
        await db.commit()
        await save_file_as_data(
            upload_file=image,
            directory="memes",
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
    else:
        return meme


@module.router.get(
    "/memes/{meme_id}/vote",
    status_code=200,
    response_model=schemas_cmm.Vote,
)
async def get_vote(
    meme_id: uuid.UUID,
    user_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user()),
):
    """
    Get a meme caracteristics using its id
    """
    vote = await cruds_cmm.get_vote(db=db, meme_id=meme_id, user_id=user_id)
    if vote is None:
        raise HTTPException(
            status_code=204, detail="The meme has no vote from this user"
        )

    return vote


@module.router.get(
    "/memes/votes/{vote_id}",
    status_code=200,
    response_model=schemas_cmm.Vote,
)
async def get_vote_by_id(
    vote_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user()),
):
    """
    Get a meme caracteristics using its id
    """
    vote = await cruds_cmm.get_vote_by_id(db=db, vote_id=vote_id)
    if vote is None:
        raise HTTPException(status_code=204, detail="The vote does not exist")

    return vote


@module.router.post(
    "/memes/{meme_id}/vote",
    response_model=schemas_cmm.Vote,
    status_code=201,
)
async def add_vote(
    meme_id: uuid.UUID,
    positive: bool,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user()),
):
    """
    Add a new vote for the user to a meme from its id
    """
    try:
        vote_id = uuid.uuid4()
        vote = models_cmm.Vote(
            id=vote_id,
            meme_id=meme_id,
            user_id=user.id,
            positive=positive,
        )
        cruds_cmm.add_vote(db=db, vote=vote)
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    else:
        return vote


@module.router.delete(
    "/memes/{meme_id}/vote",
    status_code=201,
)
async def delete_vote(
    meme_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user()),
):
    """
    Remove the vote from the user if it exists
    """
    vote = await cruds_cmm.get_vote(db=db, meme_id=meme_id, user_id=user.id)
    if vote is None:
        raise HTTPException(status_code=404, detail="The vote does not exist")
    try:
        await cruds_cmm.delete_vote(db=db, vote_id=vote.id)
        await db.commit()
    except Exception:
        await db.rollback()
        raise


@module.router.patch(
    "/memes/{meme_id}/vote",
    status_code=201,
)
async def update_vote(
    meme_id: uuid.UUID,
    positive: bool,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user()),
):
    """
    Update a vote from the user if it exists even if vote is already at the right positivity
    """
    vote = await cruds_cmm.get_vote(db=db, meme_id=meme_id, user_id=user.id)
    if vote is None:
        raise HTTPException(status_code=404, detail="The vote does not exist")
    try:
        await cruds_cmm.update_vote(db=db, vote_id=vote.id, new_positive=positive)
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    else:
        vote.positive = positive
        return vote
